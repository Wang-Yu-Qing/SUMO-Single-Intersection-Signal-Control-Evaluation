import os
import math
from itertools import chain
import sys
from time import sleep
import traci
import traci.constants as tc
from Evaluation.Lane_Queue import *
from Evaluation.Signal import *
from Evaluation.SingleEvaluation import *
#from plot import plot 
#for upper dir imports:
sys.path.append("..")
from Network_Info.Get_Info import *
from PlatServer_Interactor.pg_Interactor import PG_Interactor
import matplotlib.pyplot as plt


# set subscriptions
def set_subscriptions(edgesID):
    # set subscriptions of all edges' last step vehicle ID list:
    for edgeID in edgesID:
        #traci.edge.subscribe(edgeID, [tc.LAST_STEP_VEHICLE_ID_LIST])
        traci.edge.subscribe(edgeID, [18])
# ====================================== EDGES ==================================
# edges' travel time
def get_all_edges_travel_time(edgesID):
    edges_travel_time = {}
    for edgeID in edgesID:
        edges_travel_time[edgeID] = traci.edge.getTraveltime(edgeID)
    return edges_travel_time
# ====================================== LANES ==================================
# get step's all lanes' mean speed:
def get_all_lanes_mean_speed(lanesID):
    lanes_mean_speed = {}
    for laneID in lanesID:
        lanes_mean_speed[laneID] = traci.lane.getLastStepMeanSpeed(laneID)
    return lanes_mean_speed

# get step's all lanes' stopped vehicles number:
def get_all_lanes_stop_number(lanesID):
    lanes_stop_number = {}
    for laneID in lanesID:
        lanes_stop_number[laneID] = traci.lane.getLastStepHaltingNumber(laneID)
    return lanes_stop_number

# get step's all lanes' CO2 emission:
def get_all_lanes_CO2(lanesID):
    lanes_CO2 = {}
    for laneID in lanesID:
        lanes_CO2[laneID] = traci.lane.getCO2Emission(laneID)
    return lanes_CO2
# ===============================================================================
# get step's all vehicles' ID
def get_all_vehicles_ID(edges):
    # get all vehicles' id:
    step_all_vehID = []
    for edgeID in edges:
        # get subscription result(all vehicleIDs over all edges):
        ### traci.edge.getSubscriptionResults(edgeID)'s return is a dict: {subscription content ID: ('id1', 'id2', ...)}
        # 18 is the subcription content ID
        step_all_vehID.append(list(traci.edge.getSubscriptionResults(edgeID)[18]))
    # unnest the vehicle id list:
    step_all_vehID = list(chain.from_iterable(step_all_vehID))
    return step_all_vehID

# get step's all vehicles' position
def get_all_vehicles_position(all_vehicles_ID):
    # get all vehicles' position:
    vehicles_positions = {}
    for vehID in all_vehicles_ID:
        #print(traci.vehicle.getPosition(vehID))
        vehicles_positions[vehID] = traci.vehicle.getPosition(vehID)
    return vehicles_positions

# get step's all vehicles' angle
def get_all_vehicles_angle(all_vehicles_ID):
    vehicles_angles = {}
    for vehID in all_vehicles_ID:
        #print(traci.vehicle.getAngle(vehID))
        vehicles_angles[vehID] = traci.vehicle.getAngle(vehID)
    return vehicles_angles

# get step's all vehicles' speed
def get_all_vehicles_speed(all_vehicles_ID):
    vehicles_speeds = {}
    for vehID in all_vehicles_ID:
        #print(traci.vehicle.getSpeed(vehID))
        vehicles_speeds[vehID] = traci.vehicle.getSpeed(vehID)
    return vehicles_speeds

# get step's all vehicles' shape
def get_step_vehicles_shape(all_vehicles_ID):
    vehicles_shape = {}
    for vehID in all_vehicles_ID:
        length = traci.vehicle.getLength(vehID)
        width = traci.vehicle.getWidth(vehID)
        vehicles_shape[vehID] = (length, width)
    return vehicles_shape

def find_edges_plot_ID(GISinteractor, all_edgesID, entrance_direction_dict, exit_direction_dict):
    ID_plotID = {}
    for edgeID in all_edgesID:
        try:
            roadID = GISinteractor.execute_sql('SELECT roadid FROM tbl_entrance WHERE id=\'{}\''.format(edgeID))[0][0]
            direction = GISinteractor.execute_sql('SELECT direction FROM tbl_road WHERE id=\'{}\''.format(roadID))[0][0]
            plotID = entrance_direction_dict[direction].replace('车', '')
            ID_plotID[edgeID] = plotID
        except:
            roadID = GISinteractor.execute_sql('SELECT roadid FROM tbl_exit WHERE id=\'{}\''.format(edgeID))[0][0]
            direction = GISinteractor.execute_sql('SELECT direction FROM tbl_road WHERE id=\'{}\''.format(roadID))[0][0]
            plotID = exit_direction_dict[direction].replace('车', '')
            ID_plotID[edgeID] = plotID
    return ID_plotID 

# find all entrance lanes' 'direction-lanenumber' ID for plot, return {'originID':'plotID'}
def find_entrance_lanes_plot_ID(GISinteractor, all_lanesID, entrance_direction_dict, exit_direction_dict):
    ID_plotID = {}
    for laneID in all_lanesID:
        # get edgeID and laneNumber
        edgeID, laneNumebr = laneID.split('_')
        try:
            # entrance
            # get roadID
            roadID = GISinteractor.execute_sql('SELECT roadid FROM tbl_entrance WHERE id=\'{}\''.format(edgeID))[0][0]
            # get road position
            position = GISinteractor.execute_sql('SELECT direction FROM tbl_road WHERE id=\'{}\''.format(roadID))[0][0]
            ID_plotID[laneID] = (entrance_direction_dict[position]+'_'+laneNumebr)
        except:
            # exit
            # get roadID
            roadID = GISinteractor.execute_sql('SELECT roadid FROM tbl_exit WHERE id=\'{}\''.format(edgeID))[0][0]
            # get road position
            position = GISinteractor.execute_sql('SELECT direction FROM tbl_road WHERE id=\'{}\''.format(roadID))[0][0]
            ID_plotID[laneID] = (exit_direction_dict[position]+'_'+laneNumebr)           
    return ID_plotID




##=============================================================== CLASS: SUMO_Interactor =============================================================
class SUMO_Interactor(object):
    # Initialization:
    def __init__(self, cfgfile):
        if cfgfile.split('.')[-1] != 'cfg':
            print('PLEAS INPUT A sumo.cfg file')
        # get .net.xml file root:
        root = get_net_xml_root(cfgfile)
        # get edges ID:
        self.EdgID = get_all_edgesID(root)
        # get lanes ID:
        self.lanesID = get_all_lanes_ID(root)
        # get lanes plot ID
        GISinteractor = PG_Interactor('GISDB', 'postgres', '123456', '10.10.201.5', '54324')
        GISinteractor.make_cursor()
        entrance_direction_dict = {1:'东进口车道', 2:'西进口车道', 3:'南进口车道', 4:'北进口车道', 5:'东北进口车道', 6:'西北进口车道', 7:'东南进口车道', 8:'西南进口车道'}
        exit_direction_dict = {1:'东出口车道', 2:'西出口车道', 3:'南出口车道', 4:'北出口车道', 5:'东北出口车道', 6:'西北出口车道', 7:'东南出口车道', 8:'西南出口车道'}
        self.edgesID_plotID = find_edges_plot_ID(GISinteractor, self.EdgID, entrance_direction_dict, exit_direction_dict)
        self.lanesID_plotID = find_entrance_lanes_plot_ID(GISinteractor, self.lanesID, entrance_direction_dict, exit_direction_dict)
        # diction for all lanes' accumulative plot data, each step's data will append into it, add list for each lane if new plot data needed
        # structure: {laneID:[[allstopnumber], [allmeanspeed], [allCO2]]} 
        self.all_accu_data = {k:[[], [], []] for k in self.lanesID}
        # get lanes length:
        self.lanesLength = get_all_lanes_length(root)
        # get all lanearea detectors' ID
        self.lane_detecID = get_all_lanearea_detec_ID(cfgfile)
        # get lane-linkIndex relation
        self.lane_linkIndex = get_Lane_LinkIndex_relation(root)
        #print(lane_linkIndex)
        # get all induction loop detectors' ID:
        self.induction_detecID = get_all_induction_detec_ID(cfgfile)
        # call sumo-gui.exe via cmd
        #sumoCMD = ["sumo-gui.exe", "-c", cfgfile]
        # call sumo.exe via cmd
        sumoCMD = ["sumo.exe", "-c", cfgfile]
        # start simulatingconnection (before this step, traci.xxx.xxx can't be used ! )
        traci.start(sumoCMD)
        set_subscriptions(self.EdgID) #subscription
        self.previous_step_phase = 0 # initial previous phase for phase listener
        self.phases_flow = [0, 0, 0, 0] # for phase flow plot]
        self.all_phases_flow = []
        self.phases_id = ['相位一', '相位二', '相位三', '相位四']
        self.current_cycle_id = 1
        self.all_cycles_id = [1]
        self.current_phase_id = 0
        self.all_phases_id = [1] 
        self.all_quotas = []
        self.all_step_vehicle_number = []   
        self.step = 0
        self.acctime = [0] # for accumulative plot
        self.all_efficiency = []
        print('Initialization success!')

    def vehicles(self):
        self.VehIDs = get_all_vehicles_ID(self.EdgID) # veh IDs
        self.VehPos = get_all_vehicles_position(self.VehIDs) # veh Positions
        self.VehAng = get_all_vehicles_angle(self.VehIDs) # veh Angles
        self.VehSpe = get_all_vehicles_speed(self.VehIDs) # veh Speeds
        self.VehShape = get_step_vehicles_shape(self.VehIDs) # veh Shape

    def edges_lanes(self):
        # ===== ALL EDGES' TRAVEL TIME ========================================================
        edges_travel_time = get_all_edges_travel_time(self.EdgID)
        # replace edeges ID with plot ID
        plotID = [self.edgesID_plotID[x] for x in list(edges_travel_time.keys())]
        self.edges_travel_time = {new_k:v for new_k, v in zip(plotID, edges_travel_time.values())}
        # ===== ALL LANES' STOP NUMBER ========================================================
        all_lanes_stop_number = get_all_lanes_stop_number(self.lanesID)
        for k, v in all_lanes_stop_number.items():
            self.all_accu_data[k][0].append(v)
        # ==== ALL LANES' ACCUMULATIVE MEAN SPEED ========================================================
        all_lanes_mean_speed = get_all_lanes_mean_speed(self.lanesID)
        for k, v in all_lanes_mean_speed.items():
            # add some speed deviation (change when speed limitation changed):
            if v > 40: 
                self.all_accu_data[k][1].append(v*np.random.normal(1, 0.1))
            else:
                self.all_accu_data[k][1].append(v)
        # ==== ALL LANE'S CO2 EMISSION ========================================================
        self.all_lanes_CO2 = get_all_lanes_CO2(self.lanesID)
        # ==== LANE'S QUEUE ==============================================================
        self.LanesQueueRatio = get_all_lanes_queue_ratio(self.lane_detecID, self.lanesLength) # all lanes' queue ratio
        # self.top_three_QueueRatio = get_top_three_lane_queue_ratio(self.LanesQueueRatio) # get top three lane queue ratio
        # self.mean_QueuegetRatio = get_mean_lane_queue_ratio(self.LanesQueueRatio) # get mean lane queue ratio

    def phase_efficiency(self):
        phase_change_flag, self.previous_step_phase, self.current_step_phase = phase_listener('0', self.previous_step_phase) # listen to phase change
        if phase_change_flag == 'phase changed !':
            if self.step > 0:
                if self.current_phase_duration > 3: # neglect yellow and all-red phase
                    lanes_SF = set_lanes_SF(self.phase_lanes_flow)
                    self.phase_lanes_efficiency = get_phase_lanes_efficiency(self.previous_step_phase, self.phase_lanes_flow, self.current_phase_duration, lanes_SF) # calculate last phase lanes efficiency  
                    # replace lanes id with plot ID
                    self.phase_lanes_efficiency['green_lanes_ID'] = pd.Series([self.lanesID_plotID[x] for x in self.phase_lanes_efficiency['green_lanes_ID']])
                    print('\n ========= last phase_lanes_efficiency ============= \n {}'.format(self.phase_lanes_efficiency))
                    self.all_efficiency.append([self.current_cycle_id, self.current_phase_id, self.phase_lanes_efficiency])
                    # compute last phase's all lanes flow
                    self.phases_flow[self.current_phase_id%4] = sum([x[1] for x in self.phase_lanes_flow.items()])
                    # update current phase id
                    self.current_phase_id += 1
                    # reset phase id after a cycle (actually a cycle + 3 seconds), change while number of phases changed
                    if self.current_phase_id == 4:
                        self.current_phase_id = 0
                        self.current_cycle_id += 1
            # reset for current new phase:
            self.current_phase_duration = 1
            current_green_lanes = get_current_phase_green_lanes('0', self.current_step_phase, self.lane_linkIndex)['0']
            self.phase_lanes_flow = dict(zip(current_green_lanes, [0]*len(current_green_lanes)))
        elif phase_change_flag == 'phase not changed !':
            self.phase_lanes_flow, self.vacant_lanes_number = update_current_phase_lanes_flow('0', self.phase_lanes_flow) # update current phase's each lanes flow
            self.current_phase_duration += 1
            print('\n === current_phase_duration: {} === \n === current phase_lanes_flow ===:  \n {} \n \n \n '.format(self.current_phase_duration, self.phase_lanes_flow), end = '\r')        
        else:
            print('******* PHASE LISTENING ERROR ! *******')
            return 0

    def computing_quota(self):
        #======== QUOTA COMPUTING ==================================================================
        # in yellow and all-red phase, self.phase_lanes_flow is empty due to empty current_green_lanes
        if (len(self.phase_lanes_flow)>0) & (self.step>0):
            # update quota
            QQ = queue_quota(self.LanesQueueRatio)
            EQ = efficiency_quota(self.vacant_lanes_number, len(self.phase_lanes_flow))
            TQ = travel_quota(self.edges_travel_time)
            quotas = [QQ, EQ, TQ]
            self.step_quota = quota_fusing(quotas)
            self.all_quotas.append(self.step_quota)
        elif self.step == 0: # init quota with 100 
            self.step_quota = 100
            self.all_quotas.append(self.step_quota)
        else:
            # keep the same quota as last step in order to have the same length with acctime (init quota with 100)
            # quota no change during yellow and all red phase
            self.all_quotas.append(self.step_quota)
        sleep(0.2) # pause 0.05 second before go into next loop
    
    def step_finish(self):
        # update step id
        self.step += 1
        # save all step data
        self.acctime.append(self.step)
        self.all_phases_id.append(self.current_phase_id+1)
        self.all_cycles_id.append(self.current_cycle_id)
        self.all_phases_flow.append(self.phases_flow)


# unit test:
if __name__ == "__main__":
    interactor = SUMO_Interactor(sys.argv[1])
    while True:
        # trigger simulation step
        traci.simulationStep()
        interactor.vehicles()
        interactor.edges_lanes()
        interactor.phase_efficiency()
        interactor.computing_quota()
        interactor.step_finish()
        print(interactor.step)
    traci.close()
