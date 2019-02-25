import os
import numpy as np
import pandas as pd
from pg_Interactor import PG_Interactor
#import xml.etree.cElementTree as ET
import lxml.etree as ET
import xml.etree.ElementTree as et
import sys
from itertools import chain
sys.path.append("..")
from Network_Info.Get_Info import *


class Convertor(object):
    """
    class Convertor to convert information 
    obtained from pd sql into sumo .xml 
    """
    def __init__(self, GISinter, Siginter, type = 'single'):
        self.type = type
        self.GISinteractor = GISinter
        self.Siginteractor = Siginter
        # data dictionay:
        # { index number : road direction }
        self.road_direction_dict = {1:'east', 2:'west', 3:'south', 4:'north', 5:'north-east', 6:'north-west', 7:'south-east', 8:'south-west'}
        # { edge direction index & type : edge from node position & to node position }
        self.edge_from_to_dict = {'east_entrance':'east_center', 'east_exit':'center_east', 'west_entrance':'west_center', 'west_exit':'center_west',
        'south_entrance':'south_center', 'south_exit':'center_south', 'north_entrance':'north_center', 'north_exit':'center_north'}
        # { lane turning direction index : turning direction}
        self.lane_turning_dict = {1:'l', 2:'s', 3:'r', 4:'sl', 5:'sr', 6:'t', 7:'tl', 8:'lsr', 9:'st', 10:'lr'}
        self.signal_type_dict = {1:'Veh', 2:'Bic', 3:'Ped'}
        self.signal_flow_direction_dict = {0:'None', 1:'l', 2:'s', 3:'r', 4:'sl', 5:'sr', 6:'lr', 7:'lsr', 8:'t', 9:'tl', 10:'ts', 11:'tr', 12:'tsl', 13:'tsr', 14:'tlr', 15:'tlsr', 16:'P', 17:'P1', 18:'P2'}
        
    def node_XMLgenerator(self, intersection_ID, filename):
        if self.type == 'single':
            Inter_info = self.GISinteractor.execute_sql('SELECT * FROM tbl_cross WHERE id=\'{}\''.format(intersection_ID))[0]
            #Inter_lon = Inter_info[5]
            #Inter_lat = Inter_info[6]
            x = 0.0
            y = 0.0
            # change when roads length is available
            roads_length = {'east':300, 'west':350, 'south':250, 'north':300}
            east_x = x+roads_length['east']
            west_x = x-roads_length['west']
            south_y = y-roads_length['south']
            north_y = y+roads_length['north']
            nodesX = [str(x) for x in [x, east_x, west_x, x, x]]
            nodesY = [str(y) for y in [y, y, y, south_y, north_y]]
            nodesTypes = ['traffic_light', 'priority', 'priority', 'priority', 'priority']
            # if linkcrossid is available, change this
            nodes_position = ['center', 'east', 'west', 'south', 'north']
            nodesID = [str(x) for x in range(len(nodesX))]
            nodes_info = pd.DataFrame({'nodeID':nodesID, 'nodeX':nodesX, 'nodeY':nodesY, 'nodePosition':nodes_position, 'nodeTypes':nodesTypes})
            # creat XML:
            root = ET.Element('nodes')
            for i in range(len(nodesX)):
                ET.SubElement(root, "node", id=nodesID[i], x=nodesX[i], y=nodesY[i], type=nodesTypes[i])
            tree = ET.ElementTree(root)
            tree.write(filename, pretty_print = True)
            self.nodes_info = nodes_info
            self.roads_length = roads_length
            
    def get_edges_info(self, intersection_ID):
        # find roads information:
        roads = self.GISinteractor.execute_sql('SELECT * FROM tbl_road WHERE crossid=\'{}\''.format(intersection_ID))
        # get roads' ID:
        roadsID = [x[0] for x in roads]
        # get entrances information:
        entrancesID = []
        entrancesDirection = []
        entranceLength = []
        for roadID in roadsID:
            enID = self.GISinteractor.execute_sql('SELECT * FROM tbl_entrance WHERE roadid=\'{}\''.format(roadID))[0][0]
            enDir = self.GISinteractor.execute_sql('SELECT * FROM tbl_road WHERE id=\'{}\''.format(roadID))[0][5]
            if enDir == 1:
                enDir = 'east'
            elif enDir == 2:
                enDir = 'west'
            elif enDir == 3:
                enDir = 'south'
            else:
                enDir = 'north'
            entrancesID.append(enID)
            entrancesDirection.append(enDir)
            entranceLength.append(self.roads_length[enDir])
        ## get number of lanes on each entrances:
        ent_lanes_num = []
        for entID in entrancesID:
             lane_number = len(self.GISinteractor.execute_sql('SELECT * FROM tbl_lane WHERE sourceid=\'{}\''.format(entID)))
             ent_lanes_num.append(lane_number)
        # get exits information:
        exitsID = []
        exitsDirection = []
        exitLength = []
        for roadID in roadsID:
            exID = self.GISinteractor.execute_sql('SELECT * FROM tbl_exit WHERE roadid=\'{}\''.format(roadID))[0][0]
            exDir = self.GISinteractor.execute_sql('SELECT * FROM tbl_road WHERE id=\'{}\''.format(roadID))[0][5]
            if exDir == 1:
                exDir = 'east'
            elif exDir == 2:
                exDir = 'west'
            elif exDir == 3:
                exDir = 'south'
            else:
                exDir = 'north'
            exitsID.append(exID)
            exitsDirection.append(exDir)
            exitLength.append(self.roads_length[enDir])
        ## get number of lanes on each exits:
        exi_lanes_num = []
        for exiID in exitsID:
             lane_number = len(self.GISinteractor.execute_sql('SELECT * FROM tbl_lane WHERE sourceid=\'{}\''.format(exiID)))
             exi_lanes_num.append(lane_number)
        # merge entrances and exits into edges:
        edgetype = ['entrance']*len(entrancesID) + ['exit']*len(exitsID)
        edges_info = pd.DataFrame({'edge_id':entrancesID+exitsID, 'edge_direction':entrancesDirection+exitsDirection, 
                                   'lanes_number':ent_lanes_num+exi_lanes_num, 'edge_type':edgetype, 'edge_length':entranceLength+exitLength})
        # get each edges' from and to node:    
        ## if linkcrossid is available, get edge direction via linkcrossid and crossid
        temp = self.nodes_info
        from_nodeID = []
        to_nodeID = []
        for index, row in edges_info.iterrows():
            if (row['edge_direction'] == 'east') & (row['edge_type'] == 'entrance'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='east'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])    
            elif (row['edge_direction'] == 'east') & (row['edge_type'] == 'exit'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='east'])
            elif (row['edge_direction'] == 'west') & (row['edge_type'] == 'entrance'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='west'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])   
            elif (row['edge_direction'] == 'west') & (row['edge_type'] == 'exit'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='west'])
            elif (row['edge_direction'] == 'south') & (row['edge_type'] == 'entrance'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='south'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])
            elif (row['edge_direction'] == 'south') & (row['edge_type'] == 'exit'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='south'])
            elif (row['edge_direction'] == 'north') & (row['edge_type'] == 'entrance'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='north'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])
            elif (row['edge_direction'] == 'north') & (row['edge_type'] == 'exit'):
                from_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='center'])
                to_nodeID.append(temp['nodeID'].loc[temp['nodePosition']=='north'])
        edges_info['from_node'] = [str(int(x)) for x in from_nodeID]
        edges_info['to_node'] = [str(int(x)) for x in to_nodeID]
        self.edges_info = edges_info
        
    def edge_XMLgenerator(self, filename):
        temp = self.edges_info
        # creat XML:
        root = ET.Element('edges')
        for index, row in temp.iterrows():
            # speed limit is 45 km/h
            ET.SubElement(root, "edge", id_=row['edge_id'], from_=row['from_node'], to=row['to_node'], speed = '45', numLanes=str(row['lanes_number']))
        tree = ET.ElementTree(root)
        tree.write(filename, pretty_print = True)
        # replace id_ and from_
        with open(filename, 'r+', encoding = 'utf-8') as f:
            tree = et.parse(f)
            root = tree.getroot()
            for edge in root:
                # creat and copy 
                edge.attrib['id'] = edge.attrib['id_']
                edge.attrib['from'] = edge.attrib['from_']
                # delete old
                del edge.attrib['id_']
                del edge.attrib['from_']
            tree.write(filename)

    def get_lanes_info(self):
        edgesID = self.edges_info['edge_id']
        lanes_info = []
        for edgeID in edgesID:
            # select lane's info via edgeID(entrance & exit ID)
            rows = GISinteractor.execute_sql('SELECT * FROM tbl_lane WHERE sourceid=\'{}\''.format(edgeID))
            # sort list via number:
            ## convert str to int:
            for i in range(len(rows)):
                rows[i] = list(rows[i])
                rows[i][2] = int(rows[i][2])
            rows = sorted(rows, key=(lambda x:x[2]))
            # new max lane number
            maxnumber = len(rows) - 1
            newNumber = maxnumber
            for index, row in enumerate(rows):
                # replace flowDirection with str:
                if row[3] == 1:
                    row[3] = 'l'
                elif row[3] == 2:
                    row[3] = 's'
                elif row[3] == 3:
                    row[3] = 'r'
                elif row[3] == 4:
                    row[3] = 'sl'
                elif row[3] == 5:
                    row[3] = 'sr'
                elif row[3] == 6:
                    row[3] = 't'
                elif row[3] == 7:
                    row[3] = 'tl'
                elif row[3] == 8:
                    row[3] = 'lsr'
                elif row[3] == 9:
                    row[3] = 'st'
                elif row[3] == 10:
                    row[3] = 'lr'
                # add lane number from right 0 to left max
                row.append(newNumber)
                # new laneID
                row.append(edgeID + '_' + str(newNumber))
                newNumber -= 1
                lanes_info.append(row)
        lanes_info = pd.DataFrame(lanes_info)
        lanes_info.columns = ['laneID', 'edgeID', 'number', 'flowDirection', 'width', 'photo', 'laneType', 'preDirection', 'newNumber', 'newID']
        self.lanes_info = lanes_info
    
    def get_connection_info(self):
        edges_info = self.edges_info
        lanes_info = self.lanes_info
        connection_info = []
        # for every entrance edge, get each lanes' connection info
        for edgeID in pd.unique(lanes_info['edgeID']):
            # get this edge's lanes
            lanes = lanes_info.loc[lanes_info['edgeID'] == edgeID]
            # find this edge's info
            edge_info = edges_info.loc[edges_info['edge_id'] == edgeID]
            # only deal with entrance edge
            if edge_info['edge_type'].iloc[0] == 'exit':
                continue
            # get each lanes' connection info
            for index, row in lanes.iterrows():
                from_edgeID = edgeID
                # judge row' to_edgeID via lane's(edge's) direction and flowDirection:
                ## current only consider flow 'l s r'
                if edge_info['edge_direction'].iloc[0] == 'east':
                    if row['flowDirection'] == 'l':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='south')]).iloc[0]
                    elif row['flowDirection'] == 's':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='west')]).iloc[0]
                    elif row['flowDirection'] == 'r':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='north')]).iloc[0]                
                elif edge_info['edge_direction'].iloc[0] == 'west':
                    if row['flowDirection'] == 'l':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='north')]).iloc[0]
                    elif row['flowDirection'] == 's':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='east')]).iloc[0]
                    elif row['flowDirection'] == 'r':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='south')]).iloc[0]            
                elif edge_info['edge_direction'].iloc[0] == 'south':
                    if row['flowDirection'] == 'l':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='west')]).iloc[0]
                    elif row['flowDirection'] == 's':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='north')]).iloc[0]
                    elif row['flowDirection'] == 'r':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='east')]).iloc[0]            
                elif edge_info['edge_direction'].iloc[0] == 'north':
                    if row['flowDirection'] == 'l':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='east')]).iloc[0]
                    elif row['flowDirection'] == 's':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='south')]).iloc[0]
                    elif row['flowDirection'] == 'r':
                        to_edgeID = (edges_info['edge_id'].loc[(edges_info['edge_type']=='exit')&(edges_info['edge_direction']=='west')]).iloc[0]            
                from_laneNumber = row['newNumber']
                # get to_lanes newNumber via to_edgeID:
                to_lanesNumber = list(lanes_info['newNumber'].loc[lanes_info['edgeID']==to_edgeID])
                # generate connection info for this lane:
                for num in to_lanesNumber:
                    connection_info.append([from_edgeID, to_edgeID, from_laneNumber, num])
        connection_info = pd.DataFrame(connection_info)
        connection_info.columns = ['from_edgeID', 'to_edgeID', 'from_laneNumber', 'to_laneNumber']        
        self.connection_info = connection_info

    def con_XMLgenerator(self, filename):
        connection_info = self.connection_info
        root = ET.Element('connections')
        for index, row in connection_info.iterrows():
            ET.SubElement(root, "connection", from_ = row['from_edgeID'], to = row['to_edgeID'], fromLane = str(row['from_laneNumber']), toLane = str(row['to_laneNumber']))
        tree = ET.ElementTree(root)
        tree.write(filename, pretty_print = True)
        with open(filename, 'r+', encoding = 'utf-8') as f:
            tree = et.parse(f)
            root = tree.getroot()
            for con in root:
                con.attrib['from'] = con.attrib['from_']
                del con.attrib['from_']
            tree.write(filename)
                       
    def net_XMLgenerator(self, NodeXml, EdgeXml, ConXml, output):
        # run netconvert via cmd:
        flag = os.system('netconvert --node-files={} --edge-files={} --connection-files={} --output-file={}'.format(NodeXml, EdgeXml, ConXml, output))
        if flag == 0:
            print('Successfully created {} in {}!'.format(output, os.getcwd()))
            self.netXMLfile = output
    
    def update_connection_info(self):
        connection_info = self.connection_info
        filename = self.netXMLfile
        linkIndex = []
        tree = et.parse(filename)
        root = tree.getroot()
        linkIndex = []
        flowDirection = []
        for index, row in connection_info.iterrows():
            from_edgeID = row['from_edgeID']
            to_edgeID = row['to_edgeID']
            from_laneNumber = str(row['from_laneNumber']) # conver to string to match the type in XML element's attribute
            to_laneNumber = str(row['to_laneNumber'])
            for con in root:
                if (con.tag == 'connection') & ('linkIndex' in con.attrib.keys()):
                    if (con.attrib['from'] == from_edgeID) & (con.attrib['to'] == to_edgeID) & (con.attrib['fromLane'] == from_laneNumber) & (con.attrib['toLane'] == to_laneNumber):                 
                        linkIndex.append(con.attrib['linkIndex'])
                        flowDirection.append(con.attrib['dir'])
        connection_info['linkIndex'] = pd.Series(linkIndex)
        connection_info['flowDirection'] = pd.Series(flowDirection)
        self.connection_info = connection_info
    
    def get_plan_info(self, crossID):
        # get plan info
        rows = self.Siginteractor.execute_sql('SELECT * FROM tbl_plan WHERE crossid=\'{}\''.format(crossID))
        plan_info = []
        for row in rows:
            plan_info.append([row[0], row[1], row[3], row[4], row[5]])
        plan_info = pd.DataFrame(plan_info)
        plan_info.columns = ['planID', 'crossID', 'planName', 'planCycle', 'planOffset']
        return plan_info
    
    def get_plan_stage_info(self, planID):
        # get plan stage info:
        rows = self.Siginteractor.execute_sql('SELECT * FROM tbl_plan_stage WHERE planid=\'{}\''.format(planID))
        plan_stage_info = []
        for row in rows:
            plan_stage_info.append([row[2], row[1], row[3], row[5], row[6], row[9]])
        plan_stage_info = pd.DataFrame(plan_stage_info)
        plan_stage_info.columns = ['stageID', 'planID', 'stageSeq', 'stageMaxG', 'stageMinG', 'stageTime']
        return plan_stage_info
    
    def get_stage_signalgroup_info(self, stagesID):
        """
        input one plan's all stages' ID as an iterator
        return stagesID-signalgroupsID
        """
        stage_signalgroup_info = []
        for stageID in stagesID:
            rows = self.Siginteractor.execute_sql('SELECT * FROM tbl_stage_signalgroup WHERE stageid=\'{}\''.format(stageID))
            for row in rows:
                stageID = row[1] 
                signalgroupID = row[2]
                stage_signalgroup_info.append([stageID, signalgroupID])
        stage_signalgroup_info = pd.DataFrame(stage_signalgroup_info)
        stage_signalgroup_info.columns = ['stageID', 'signalgroupID']
        self.stage_signalgroup_info = stage_signalgroup_info

    def get_signalgroup_info(self):
            stage_signalgroup_info = self.stage_signalgroup_info
            signal_group_info = []
            for index, row in stage_signalgroup_info.iterrows():
                stageID = row['stageID']
                signalgroup_row = SIGinteractor.execute_sql('SELECT * FROM tbl_signalgroup WHERE id=\'{}\''.format(row['signalgroupID']))[0]
                signalgroupID = signalgroup_row[0]
                crossID = signalgroup_row[1]
                type_ = signalgroup_row[4]
                if type_ == 1:
                    type_ = 'Veh'
                elif type_ == 2:
                    type_ = 'Bic'
                else:
                    type_ = 'Ped'
                direction = signalgroup_row[5]
                if direction == 1:
                    direction = 'east'
                elif direction == 2:
                    direction = 'west'
                elif direction == 3:
                    direction = 'south'
                elif direction == 4:
                    direction = 'north'
                elif direction == 5:
                    direction = 'east-north'
                elif direction == 6:
                    direction = 'west-north'
                elif direction == 7:
                    direction = 'east-south'
                elif direction == 8:
                    direction = 'west-south'
                elif direction == 9:
                    direction = 'other'    
                lanesID = signalgroup_row[7]
                flowDirection = signalgroup_row[9]
                if flowDirection == 0:
                    flowDirection = 'None'
                elif flowDirection == 1:
                    flowDirection = 'l'
                elif flowDirection == 2:
                    flowDirection = 's'
                elif flowDirection == 3:
                    flowDirection = 'r'
                elif flowDirection == 4:
                    flowDirection = 'sl'
                elif flowDirection == 5:
                    flowDirection = 'sr'
                elif flowDirection == 6:
                    flowDirection = 'lr'
                elif flowDirection == 7:
                    flowDirection = 'lsr'
                elif flowDirection == 8:
                    flowDirection = 't'
                elif flowDirection == 9:
                    flowDirection = 'tl'
                elif flowDirection == 10:
                    flowDirection = 'ts'
                elif flowDirection == 11:
                    flowDirection = 'tr'
                elif flowDirection == 12:
                    flowDirection = 'tsl'
                elif flowDirection == 13:
                    flowDirection = 'tsr'
                elif flowDirection == 14:
                    flowDirection = 'tlr'
                elif flowDirection == 15:
                    flowDirection = 'tlsr'
                elif flowDirection == 16:
                    flowDirection = 'P'
                elif flowDirection == 17:
                    flowDirection = 'P1'
                elif flowDirection == 18:
                    flowDirection = 'P2'
                yellowTime = signalgroup_row[11]
                allredTime = signalgroup_row[13]
                stageTime = self.Siginteractor.execute_sql('SELECT stagetime FROM tbl_plan_stage WHERE stageid=\'{}\''.format(stageID))[0][0]
                greenTime = stageTime - allredTime - yellowTime
                signal_group_info.append([crossID, stageID, signalgroupID, type_, direction, lanesID, flowDirection, yellowTime, allredTime, greenTime])
            signal_group_info = pd.DataFrame(signal_group_info)
            signal_group_info.columns = ['crossID', 'stageID', 'signalgroupID', 'signalgroupType', 'direction', 'lanesID', 'flowDirection', 'yellowTime', 'allredTime', 'greenTime']
            self.signal_group_info = signal_group_info
    
    # def get_linkindex_info(self):
    #     tree = et.parse(self.netXMLfile)
    #     root = tree.getroot()
    #     cols = ['from', 'to', 'fromLane', 'toLane', 'tl', 'linkIndex', 'dir']
    #     linkindex_info = []
    #     for elem in root:
    #         if elem.tag == 'connection':
    #             try:
    #                 values = [elem.attrib[x] for x in cols]
    #                 linkindex_info.append(values)
    #             except:
    #                 continue
    #     linkindex_info = pd.DataFrame(linkindex_info)
    #     linkindex_info.columns = ['fromEdge', 'toEdge', 'fromLane', 'toLane', 'tlID', 'linkIndex', 'dir']
    #     self.linkindex_info = linkindex_info           

    def get_phases_state(self):
        edges_info = self.edges_info
        signal_group_info = self.signal_group_info
        connection_info = self.connection_info    
        linkIndicesNumber = len(connection_info['linkIndex'])
        # phaseID:(phase state, duration)
        phases_state = {}
        for stageID in pd.unique(signal_group_info['stageID']):
            phase_state = ['r']*linkIndicesNumber
            temp = signal_group_info.loc[signal_group_info['stageID'] == stageID]
            # for all signalgroups in the stage (phase):
            stage_greenlinkIndices = []
            allSG_yellowTime = []
            allSG_allredTime = []
            allSG_greenTime = []
            for index, row in temp.iterrows():
                if row['signalgroupType'] == 'Ped':
                    continue
                edgeID = edges_info['edge_id'].loc[(edges_info['edge_direction'] == row['direction']) & (edges_info['edge_type'] == 'entrance')].iloc[0]
                linkIndices = connection_info['linkIndex'].loc[(connection_info['flowDirection'] == row['flowDirection']) & (connection_info['from_edgeID'] == edgeID)]
                stage_greenlinkIndices.append(list(linkIndices))
                allSG_yellowTime.append(row['yellowTime'])
                allSG_allredTime.append(row['allredTime'])
                allSG_greenTime.append(row['greenTime'])
            stage_greenlinkIndices = list(chain.from_iterable(stage_greenlinkIndices))
            # conver stage_greenlinkIndices to green phase state:
            stage_greenlinkIndices = [int(x) for x in stage_greenlinkIndices]
            for GI in stage_greenlinkIndices:
                phase_state[GI] = 'G'
            # get yellow phase state (replace 'G' with 'y')
            phase_state_y = list(map(lambda x: x if x=='r' else 'y', phase_state))
            # get allred phase state
            phase_state_r = ['r']*linkIndicesNumber
            # get stage green, yellow, red duration
            if (len(set(allSG_allredTime))==1) & (len(set(allSG_yellowTime))==1) & (len(set(allSG_greenTime))==1):
                green_duration = np.mean(allSG_greenTime)
                yellow_duration = np.mean(allSG_yellowTime)
                allred_duration = np.mean(allSG_allredTime)
            else:
                print('stage {}\'s signalgroups\' y, r, g time is different!',format(stageID))
            # generate phase state for this stage's green, yellow, allred phase:
            phases_state[stageID+'-'+'green'] = (phase_state, green_duration)
            phases_state[stageID+'-'+'yellow'] = (phase_state_y, yellow_duration)
            phases_state[stageID+'-'+'allred'] = (phase_state_r, allred_duration)   
            self.phases_state = phases_state
            
    def addXML_generator(self, filename, inducLoopfile, insinducLoopfile, laneAreafile, position = 20, ):
        phases_state = self.phases_state
        edges_info = self.edges_info
        lanes_info = self.lanes_info
        root = ET.Element('additional')
        # TLS program:
        tlLogic = ET.SubElement(root, "tlLogic", id="0", programID="my_program", offset="0", type="static")
        for phase in phases_state.items():
            ET.SubElement(tlLogic, "phase", duration = str(phase[1][1]), state = ''.join(phase[1][0]))
        # detectors:
        # get entrance edges' ID
        edgesID = edges_info['edge_id'].loc[edges_info['edge_type'] == 'entrance']
        # get entrance lanes' newID
        lanesID = lanes_info['newID'].loc[np.isin(lanes_info['edgeID'],edgesID)]    
        # generate induction loop detectors, instant induction loop detectors and lane area detectors element
        for laneID in lanesID:
            # get lane's length
            edgeID = lanes_info['edgeID'].loc[lanes_info['newID'] == laneID].iloc[0]
            length = edges_info['edge_length'].loc[edges_info['edge_id'] == edgeID].iloc[0]
            # instant induction loop detectors
            ET.SubElement(root, "instantInductionLoop", id=laneID, lane=laneID, pos=str(length-position), file=insinducLoopfile)
            # induction loop detectors
            ET.SubElement(root, "inductionLoop", id=laneID, lane=laneID, pos=str(length-position), freq="300", file=inducLoopfile)
            # lane area detector element
            ET.SubElement(root, "laneAreaDetector", id=laneID, lane=laneID, freq="300", file=laneAreafile)
        # veh types (speed distribution):
        #ET.SubElement(root, "vType", id="passenger", speedFactor="normc(1,0.15,0.2,2)", vClass='passenger')
        #ET.SubElement(root, "vType", id="passenger", speedFactor="1", speedDev="0.1", vClass="passenger")
        tree = ET.ElementTree(root)
        tree.write(filename, pretty_print = True)
        self.addfile = filename

    # def random_trip_generator(self):
    #     flag = os.system('D:\\Sumo\\tools\\python randomTrips.py -n {} -o random.trips.xml'.format(self.netXMLfile))
    #     if flag == 0:
    #         print('Successfully generated random.trips.xml)
    #         self.tripsXML = "random.trips.xml"

    def SUMO_cfg_generator(self, filename):
        root = ET.Element("configuration")
        input_ = ET.SubElement(root, "input")
        ET.SubElement(input_, "n", v = self.netXMLfile)
        ET.SubElement(input_, "additional-files", value = self.addfile)
        ET.SubElement(input_, "r", v = 'trips.trips.xml')
        tree = ET.ElementTree(root)
        tree.write(filename, pretty_print = True)
        self.cfgfile = filename


                

# for unit debugging:
if __name__ == '__main__':
    GISinteractor = PG_Interactor('GISDB', 'postgres', '123456', '10.10.201.5', '54324')
    SIGinteractor = PG_Interactor('SignalStaticDB', 'postgres', '123456', '10.10.201.5', '54320')
    GISinteractor.make_cursor()
    SIGinteractor.make_cursor()
    #tbl_cross = GISinteractor.execute_sql('SELECT * FROM tbl_cross LIMIT 10')
    # get intersection table:
    tbl_cross = GISinteractor.execute_sql('SELECT * FROM tbl_cross')
    colnames = GISinteractor.execute_sql('SELECT column_name FROM information_schema.columns \
                                    WHERE table_schema=\'public\' and table_name=\'tbl_cross\'')
    tbl_cross = pd.DataFrame(tbl_cross)
    tbl_cross.columns = [x[0] for x in colnames]
    # get target_intersection ID via name
    target_interID = GISinteractor.get_intersection_ID('王宇清的测试路口')
    # generate convertor
    Myconvertor = Convertor(GISinter = GISinteractor, Siginter = SIGinteractor)
    # generate node.xml
    Myconvertor.node_XMLgenerator(target_interID, 'test.node.xml')
    # generate edg.xml
    Myconvertor.get_edges_info(target_interID)
    Myconvertor.edge_XMLgenerator('test.edg.xml')
    # get lanes_info:
    Myconvertor.get_lanes_info()
    # get connection_info
    Myconvertor.get_connection_info()
    # gnerate con.xml
    Myconvertor.con_XMLgenerator('test.con.xml')
    # gnerate net.xml
    Myconvertor.net_XMLgenerator('test.node.xml', 'test.edg.xml', 'test.con.xml', 'test.net.xml')
    # update connection_info based on .net.xml file
    Myconvertor.update_connection_info()
    # get timing plan:
    plan_info = Myconvertor.get_plan_info(target_interID)
    # for example, get one timing plan ID:
    planID = plan_info['planID'][0]
    # get this plan's stage info
    plan_stage_info = Myconvertor.get_plan_stage_info(planID)
    # get stage-signalgroup info
    Myconvertor.get_stage_signalgroup_info(plan_stage_info['stageID'])
    # get signal group info
    Myconvertor.get_signalgroup_info()
    # get phases state info
    Myconvertor.get_phases_state()
    # generate additional XML file
    Myconvertor.addXML_generator('test.additional.xml', 'inducLoopfile.E1.xml', 'insinduc_loop.ins.xml', 'lane_area.E2.xml')
    # generate config file
    Myconvertor.SUMO_cfg_generator('test.sumo.cfg')



















