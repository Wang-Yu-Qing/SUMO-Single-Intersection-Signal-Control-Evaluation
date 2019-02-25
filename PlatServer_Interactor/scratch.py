# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 16:04:25 2018

@author: lenovo
"""
#=============== get_lanes_info(self)
edgesID = edges_info['edge_id']
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
        newNumber -= 1
        lanes_info.append(row)
lanes_info = pd.DataFrame(lanes_info)
lanes_info.columns = ['laneID', 'edgeID', 'number', 'flowDirection', 'width', 'photo', 'laneType', 'preDirection', 'newNumber']

#============= get_connection_info(self)
edges_info
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

#============ con_XMLgenerator(self, filename)
connection_info
filename = 'test.con.xml'
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
    
# === update connection info
## add column 'linkIndex' to connection_info
connection_info
filename = 'test.net.xml'
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

    
# === get signal group (add duration)
def get_signalgroup_info(self, stage_signalgroup_info):
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
            signal_group_info.append([crossID, stageID, signalgroupID, type_, direction, lanesID, flowDirection])
        signal_group_info = pd.DataFrame(signal_group_info)
        signal_group_info.columns = ['crossID', 'stageID', 'signalgroupID', 'signalgroupType', 'direction', 'lanesID', 'flowDirection']
        return signal_group_info


               
    
# === get_phases_state
linkindex_info = Myconvertor.linkindex_info
edges_info = Myconvertor.edges_info
signalgroup_info   
connection_info = Myconvertor.connection_info    
linkIndicesNumber = len(connection_info['linkIndex'])
# phaseID:state
phases_state = {}
for stageID in pd.unique(signalgroup_info['stageID']):
    phase_state = ['r']*linkIndicesNumber
    temp = signalgroup_info.loc[signalgroup_info['stageID'] == stageID]
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
    # generate phase stae for this stage's green, yellow, allred phase:
    phases_state[stageID+'-'+'green'] = (phase_state, green_duration)
    phases_state[stageID+'-'+'yellow'] = (phase_state_y, yellow_duration)
    phases_state[stageID+'-'+'allred'] = (phase_state_r, allred_duration)

        
# == generate TLS program and detectors in additional XML file 
# TLS program:
phases_state
filename =  'test.additional.xml'
insLoopfile = 'ins_loop.ins.xml'
position = 20
laneAreafile = 'lane_area.E2.xml'
edges_info
lanes_info
root = ET.Element('additional')
tlLogic = ET.SubElement(root, "tlLogic", id="0", programID="my_program", offset="0", type="static")
for phase in phases_state.items():
    ET.SubElement(tlLogic, "phase", duration = str(phase[1][1]), state = ''.join(phase[1][0]))
# detectors:
# get entrance edges' ID
edgesID = edges_info['edge_id'].loc[edges_info['edge_type'] == 'entrance']
# get entrance lanes' newID
lanesID = lane_info['newID'].loc[np.isin(lane_info['edgeID'],edgesID)]    
# generate instant loop detectors and lane area detectors element
for laneID in lanesID:
    # get lane's length
    edgeID = lanes_info['edgeID'].loc[lanes_info['newID'] == laneID].iloc[0]
    length = edges_info['edge_length'].loc[edges_info['edge_id'] == edgeID].iloc[0]
    # instant loop detectors
    ET.SubElement(root, "instantInductionLoop", id=laneID, lane=laneID, pos=str(length-position), file=insLoopfile)
    # lane area detector element
    ET.SubElement(root, "laneAreaDetector", id=laneID, lane=laneID, freq="20", file=laneAreafile)
tree = ET.ElementTree(root)
tree.write(filename, pretty_print = True)

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    