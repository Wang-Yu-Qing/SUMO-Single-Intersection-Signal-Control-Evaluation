import os
import math
from itertools import chain
import sys
from time import sleep
from pylab import * # for show chinese characters in plot
mpl.rcParams['font.sans-serif'] = ['SimHei'] 

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




##=============================================================== main loop that interact with SUMO via TraCI =============================================================
def main(cfgfile):
    if cfgfile.split('.')[-1] != 'cfg':
        print('PLEAS INPUT A sumo.cfg file')
        return False
    # get .net.xml file root:
    root = get_net_xml_root(cfgfile)
    # get edges ID:
    EdgID = get_all_edgesID(root)
    # get lanes ID:
    lanesID = get_all_lanes_ID(root)
    # get lanes plot ID
    GISinteractor = PG_Interactor('GISDB', 'postgres', '123456', '10.10.201.5', '54324')
    GISinteractor.make_cursor()
    entrance_direction_dict = {1:'东进口车道', 2:'西进口车道', 3:'南进口车道', 4:'北进口车道', 5:'东北进口车道', 6:'西北进口车道', 7:'东南进口车道', 8:'西南进口车道'}
    exit_direction_dict = {1:'东出口车道', 2:'西出口车道', 3:'南出口车道', 4:'北出口车道', 5:'东北出口车道', 6:'西北出口车道', 7:'东南出口车道', 8:'西南出口车道'}
    lanesID_plotID = find_entrance_lanes_plot_ID(GISinteractor, lanesID, entrance_direction_dict, exit_direction_dict)
    # diction for all lanes' accumulative plot data, each step's data will append into it, add list for each lane if new plot data needed
    # structure: {laneID:[[allstopnumber], [allmeanspeed], [allCO2]]} 
    all_accu_data = {k:[[], [], []] for k in lanesID}
    # get lanes length:
    lanesLength = get_all_lanes_length(root)
    # get all lanearea detectors' ID
    lane_detecID = get_all_lanearea_detec_ID(cfgfile)
    # get lane-linkIndex relation
    lane_linkIndex = get_Lane_LinkIndex_relation(root)
    #print(lane_linkIndex)
    # get all induction loop detectors' ID:
    induction_detecID = get_all_induction_detec_ID(cfgfile)
    # call sumo-gui.exe via cmd
    #sumoCMD = ["sumo-gui.exe", "-c", cfgfile]
    # call sumo.exe via cmd
    sumoCMD = ["sumo.exe", "-c", cfgfile]
    # start simulatingconnection (before this step, traci.xxx.xxx can't be used ! )
    traci.start(sumoCMD)
    set_subscriptions(EdgID) #subscription
    previous_step_phase = 0 # initial previous phase for phase listener
    # for dynamic plot:
    plt.ion()
    fig = plt.figure(figsize=(15, 10))
    #fig.subplots_adjust(hspace = 5)   # revise subplot h space
    # different grids for different h spaces
    gs1 = GridSpec(10,16, hspace=5)
    gs2 = GridSpec(10,16, hspace=1, wspace=1, top=0.8)
    acctime = [] # for accumulative plot
    phases_flow = [0, 0, 0, 0] # for phase flow plot
    phases_id = ['相位一', '相位二', '相位三', '相位四']
    current_cycle_id = 1
    current_phase_id = 0 
    SQ = []
    all_step_vehicle_number = []   
    step = 0
    while step < 1000:
        ## within each simulation step:
        traci.simulationStep()
        VehIDs = get_all_vehicles_ID(EdgID) # veh IDs
        VehPos = get_all_vehicles_position(VehIDs) # veh Positions
        VehAng = get_all_vehicles_angle(VehIDs) # veh Angles
        VehSpe = get_all_vehicles_speed(VehIDs) # veh Speeds
        VehShape = get_step_vehicles_shape(VehIDs) # veh Shape
# =============================================================== ALL EDGES' TRAVEL TIME ========================================================
        edges_travel_time = get_all_edges_travel_time(EdgID)
# =============================================================== ALL LANES' STOP NUMBER ========================================================
        all_lanes_stop_number = get_all_lanes_stop_number(lanesID)
        for k, v in all_lanes_stop_number.items():
            all_accu_data[k][0].append(v)
# =============================================================== ALL LANES' ACCUMULATIVE MEAN SPEED ========================================================
        all_lanes_mean_speed = get_all_lanes_mean_speed(lanesID)
        for k, v in all_lanes_mean_speed.items():
            # add some speed deviation:
            if v > 40: 
                all_accu_data[k][1].append(v*np.random.normal(1, 0.1))
            else:
                all_accu_data[k][1].append(v)
# =============================================================== ALL LANE'S CO2 EMISSION ========================================================
        all_lanes_CO2 = get_all_lanes_CO2(lanesID)
# =============================================================== LANE'S QUEUE ==============================================================
        LanesQueueRatio = get_all_lanes_queue_ratio(lane_detecID, lanesLength) # all lanes' queue ratio
        top_three_QueueRatio = get_top_three_lane_queue_ratio(LanesQueueRatio) # get top three lane queue ratio
        mean_QueuegetRatio = get_mean_lane_queue_ratio(LanesQueueRatio) # get mean lane queue ratio
# =============================================================== PHASE LANES EFFICIENCY ==========================================================
        phase_change_flag, previous_step_phase, current_step_phase = phase_listener('0', previous_step_phase) # listen to phase change
        if phase_change_flag == 'phase changed !':
            if step > 0:
                if phase_duration > 3: # neglect yellow and all-red phase
                    lanes_SF = set_lanes_SF(phase_lanes_flow)
                    phase_lanes_efficiency = get_phase_lanes_efficiency(previous_step_phase, phase_lanes_flow, phase_duration, lanes_SF) # calculate last phase lanes efficiency  
                    print('\n ========= last phase_lanes_efficiency ============= \n {}'.format(phase_lanes_efficiency))
                    # compute last phase's all lanes flow
                    phases_flow[current_phase_id%4] = sum([x[1] for x in phase_lanes_flow.items()])
                    current_phase_id += 1
                    # reset phase id after a cycle (actually a cycle + 3 seconds), change while number of phases changed
                    if current_phase_id == 4:
                        current_phase_id = 0
                        current_cycle_id += 1
            # reset for current new phase:
            phase_duration = 1
            current_green_lanes = get_current_phase_green_lanes('0', current_step_phase, lane_linkIndex)['0']
            phase_lanes_flow = dict(zip(current_green_lanes, [0]*len(current_green_lanes)))
        elif phase_change_flag == 'phase not changed !':
            phase_lanes_flow, vacant_lanes_number = update_current_phase_lanes_flow('0', phase_lanes_flow) # update current phase's each lanes flow
            phase_duration += 1
            print('\n === current phase_duration: {} === \n === current phase_lanes_flow ===:  \n {} \n \n \n '.format(phase_duration, phase_lanes_flow), end = '\r')        
        else:
            print('******* PHASE LISTENING ERROR ! *******')
            break
# =============================================================== QUOTA COMPUTING ==================================================================
        if (len(phase_lanes_flow)>0) & (step>0):
             # update quota
            QQ = queue_quota(LanesQueueRatio)
            EQ = efficiency_quota(vacant_lanes_number, len(phase_lanes_flow))
            TQ = travel_quota(edges_travel_time)
            quotas = [QQ, EQ, TQ]
            SingleQuota = quota_fusing(quotas)
            SQ.append(SingleQuota)
        elif step == 0: # init quota with 100 
            SingleQuota = 100
            SQ.append(SingleQuota)
        else:
            SQ.append(SingleQuota) # keep the same quota as last step in order to have the same length with acctime (init quota with 100)
# =============================================================== DYNAMIC PLOTS  ===================================================================
        # ======== plot queue ratio
        plot_lanesID = [lanesID_plotID[x] for x in LanesQueueRatio]
        queue_ratio = list(LanesQueueRatio.values())
        # clean last plot
        if 'QRplot' in locals():
            QRplot.clear()
        QRplot = fig.add_subplot(gs1[3:6, 8:12]) # returns an axes object representing this subplot
        QRplot.set_xlabel("车道方位_编号", fontproperties="SimHei") 
        QRplot.set_ylabel("排队饱和度", fontproperties="SimHei")
        # change x axis font size
        QRplot.xaxis.set_tick_params(labelsize=2)
        QRplot.set_title("各进口车道排队饱和度", fontproperties="SimHei", fontsize = 17)
        QRplot.bar(plot_lanesID, queue_ratio, color = '#0000FF')
        # ======== plot last phase efficiency
        if phase_change_flag == 'phase changed !':
            if 'phase_lanes_efficiency' in locals():
                # clean last plot
                if 'GEplot' in locals():
                    GEplot.clear()
                GlanesID = phase_lanes_efficiency['green_lanes_ID']
                effi = phase_lanes_efficiency['efficiency']
                # get lanes's plot ID
                plot_lanesID = [lanesID_plotID[x] for x in GlanesID]
                # subplot
                GEplot = fig.add_subplot(gs2[6:10, 0:4])
                GEplot.set_xlabel("车道方位_编号", fontproperties="SimHei")
                GEplot.xaxis.set_tick_params(labelsize=5) 
                GEplot.set_ylabel("上一相位的绿灯利用率", fontproperties="SimHei") 
                GEplot.set_title("上一相位车道绿时利用率", fontproperties="SimHei", fontsize = 17)
                GEplot.bar(plot_lanesID, effi, color = '#006400')
        # ========= plot all lanes' CO2:
        if 'CO2plot' in locals():
            CO2plot.clear()
        plot_lanesID = [lanesID_plotID[x] for x in list(all_lanes_CO2.keys())]
        CO2 = list(all_lanes_CO2.values())
        CO2plot = fig.add_subplot(gs1[3:6, 12:16])
        CO2plot.set_xlabel("车道方位_编号", fontproperties="SimHei")
        CO2plot.xaxis.set_tick_params(labelsize=2) 
        CO2plot.set_ylabel("二氧化碳排放量", fontproperties="SimHei") 
        CO2plot.set_title("车道碳排放", fontproperties="SimHei", fontsize = 17)
        CO2plot.bar(plot_lanesID, CO2, color = '#32CD32')
        # ================================= plot edges' travel time
        if 'ETT_plot' in locals():
            ETT_plot.clear()
        ETT_plot = fig.add_subplot(gs1[3:6, 0:4])
        ETT_plot.set_xlabel('有向路段', fontproperties="SimHei")
        ETT_plot.xaxis.set_tick_params(labelsize=5)
        ETT_plot.set_ylabel("行程时间（秒）", fontproperties="SimHei") 
        ETT_plot.set_title("各路段行程时间", fontproperties="SimHei", fontsize = 17)
        ETT_plot.bar(list(edges_travel_time.keys()), list(edges_travel_time.values()), color = 'c')
        # ======== all vehicles' speed box plot:
        if 'AVS_plot' in locals():
            AVS_plot.clear()
        AVS_plot = fig.add_subplot(gs1[3:6, 4:8])
        AVS_plot.set_ylabel("速度（KM/H）", fontproperties="SimHei") 
        AVS_plot.set_title("车辆速度箱线图", fontproperties="SimHei", fontsize = 17)
        AVS_plot.boxplot(list(VehSpe.values()))
        # =================================================== ACCUMULATIVE PLOT ============================================================
        acctime.append(step)
        # ================================= plot entrances lanes mean speed =================================
        # east entrance:
        if 'LMS_east_plot' in locals():
            LMS_east_plot.clear()
        LMS_east_plot = fig.add_subplot(gs1[0:3, 0:4])
        LMS_east_plot.set_xlabel("时间", fontproperties="SimHei") 
        LMS_east_plot.xaxis.set_tick_params(labelsize=5)
        LMS_east_plot.set_ylabel("平均行驶速度（KM/H）", fontproperties="SimHei") 
        LMS_east_plot.set_title("东进口车道平均行驶速度", fontproperties="SimHei", fontsize = 17)
        for k, v in all_accu_data.items():
            # only plot entrance lanes:
            if (lanesID_plotID[k][1] == '进') & (lanesID_plotID[k][0] == '东'):
                LMS_east_plot.plot(acctime, v[1])
        # west entrance:
        if 'LMS_west_plot' in locals():
            LMS_west_plot.clear()
        LMS_west_plot = fig.add_subplot(gs1[0:3, 4:8])
        LMS_west_plot.set_xlabel("时间", fontproperties="SimHei") 
        LMS_west_plot.xaxis.set_tick_params(labelsize=5)
        LMS_west_plot.set_ylabel("平均行驶速度（KM/H）", fontproperties="SimHei") 
        LMS_west_plot.set_title("西进口车道平均行驶速度", fontproperties="SimHei", fontsize = 17)
        for k, v in all_accu_data.items():
            # only plot entrance lanes:
            if (lanesID_plotID[k][1] == '进') & (lanesID_plotID[k][0] == '西'):
                LMS_west_plot.plot(acctime, v[1])
        # south entrance:
        if 'LMS_south_plot' in locals():
            LMS_south_plot.clear()
        LMS_south_plot = fig.add_subplot(gs1[0:3, 8:12])
        LMS_south_plot.set_xlabel("时间", fontproperties="SimHei") 
        LMS_south_plot.xaxis.set_tick_params(labelsize=5)
        LMS_south_plot.set_ylabel("平均行驶速度（KM/H）", fontproperties="SimHei") 
        LMS_south_plot.set_title("南进口车道平均行驶速度", fontproperties="SimHei", fontsize = 17)
        for k, v in all_accu_data.items():
            # only plot entrance lanes:
            if (lanesID_plotID[k][1] == '进') & (lanesID_plotID[k][0] == '南'):
                LMS_south_plot.plot(acctime, v[1])
        # north entrance:
        if 'LMS_north_plot' in locals():
            LMS_north_plot.clear()
        LMS_north_plot = fig.add_subplot(gs1[0:3, 12:16])
        LMS_north_plot.set_xlabel("时间", fontproperties="SimHei") 
        LMS_north_plot.xaxis.set_tick_params(labelsize=5)
        LMS_north_plot.set_ylabel("平均行驶速度（KM/H）", fontproperties="SimHei") 
        LMS_north_plot.set_title("北进口车道平均行驶速度", fontproperties="SimHei", fontsize = 17)
        for k, v in all_accu_data.items():
            # only plot entrance lanes:
            if (lanesID_plotID[k][1] == '进') & (lanesID_plotID[k][0] == '北'):
                LMS_north_plot.plot(acctime, v[1])
# ======================== PLOT PHASES FLOW ================================
        explode = (0.1, 0.1, 0.1, 0.1)
        # plot when phase change! first cycle no plot 
        if (current_phase_id == 0) & (current_cycle_id > 1):
            if 'PF_plot' in locals():
                PF_plot.clear()
            PF_plot = fig.add_subplot(gs2[6:10, 4:8])
            PF_plot.set_title("上周期各相位流量", fontproperties="SimHei", fontsize = 17)
            # update plt
            # show flow value on label:
            label = [x[0]+':'+str(x[1]) for x in zip(phases_id, phases_flow)]
            PF_plot.pie(phases_flow, labels = label, shadow = True, startangle = 90, explode = explode, radius = 1.5)
            PF_plot.axis('equal')
# # ============================ PLOT QUOTA =====================================
        #===== quota - acctime plot
        if 'SQ_plot' in locals():
            SQ_plot.clear()
        SQ_plot = fig.add_subplot(gs2[6:10, 8:12])
        SQ_plot.set_xlabel("时间", fontproperties="SimHei") 
        SQ_plot.xaxis.set_tick_params(labelsize=5)
        SQ_plot.set_ylabel("评价得分", fontproperties="SimHei") 
        SQ_plot.set_title("当前评价得分:{}".format(math.floor(SingleQuota)), fontproperties="SimHei", fontsize = 20)
        SQ_plot.plot(acctime, SQ)
        # show last point's quota text
        #SQ_plot.text(acctime[-1], SingleQuota, '{}'.format(math.floor(SingleQuota)), fontsize = 15, color = 'r')

        #===== quota - number of vehicles plot
        QN_plot_scatter = fig.add_subplot(gs2[7:10, 12:15])
        QN_plot_scatter.set_xlabel("车辆数", fontproperties="SimHei") 
        QN_plot_scatter.xaxis.set_tick_params(labelsize=5)
        QN_plot_scatter.set_ylabel("评价得分", fontproperties="SimHei") 
        #QN_plot_scatter.set_title("评价得分-车辆数", fontproperties="SimHei", fontsize = 17)
        all_step_vehicle_number.append(len(VehIDs))
        # scatter plot
        # show different color according to its quota:
        if SingleQuota > 80:
            QN_plot_scatter.scatter(len(VehIDs), SingleQuota, color = 'limegreen', s = 10)
        elif SingleQuota > 60:
            QN_plot_scatter.scatter(len(VehIDs), SingleQuota, color = 'lightgreen', s = 20, alpha = 0.7)
        elif SingleQuota > 40:
            QN_plot_scatter.scatter(len(VehIDs), SingleQuota, color = 'orange', s = 30, alpha = 0.7)
        elif SingleQuota > 20:
            QN_plot_scatter.scatter(len(VehIDs), SingleQuota, color = 'red', s = 40, alpha = 0.5)
        else:
            QN_plot_scatter.scatter(len(VehIDs), SingleQuota, color = 'darkred', s = 50, alpha = 0.5)
        # histogram plot
        if ('QN_plot_hist_x' in locals()) & (('QN_plot_hist_y') in locals()):
            QN_plot_hist_x.clear()
            QN_plot_hist_y.clear()
        QN_plot_hist_x = fig.add_subplot(gs2[6:7, 12:15])
        QN_plot_hist_y = fig.add_subplot(gs2[7:10, 15:16])
        QN_plot_hist_x.hist(all_step_vehicle_number, bins = 15)
        QN_plot_hist_y.hist(SQ, orientation = 'horizontal', bins = 15)







# ===================== FIGURE TITLE ============================================
        fig.suptitle('第 {} 周期， 第 {} 相位'.format(current_cycle_id, current_phase_id+1), fontproperties="SimHei", fontsize = 25)
        plt.tight_layout()
        plt.show()
        plt.pause(0.00001)

        step += 1
        #sleep(0.02) # pause 0.05 second before go into next loop
    traci.close()


if __name__ == "__main__":
    main(sys.argv[1])
