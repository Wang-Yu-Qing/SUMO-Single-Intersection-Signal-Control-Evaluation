import os
import xml.etree.ElementTree as et

import numpy as np
import pandas as pd

import traci
import traci.constants as tc

# def get_raw_timing_plan(net_xml_root):
#     raw_timing_plan = []
#     plan_attribs = ['id', 'type', 'programID', 'offset']
#     phase_attribs = ['duration', 'state']
#     for r in net_xml_root:
#         if r.tag == 'tlLogic':
#             plan_values = [r.attrib[x] for x in plan_attribs]
#             for phase in r.findall('phase'):
#                 phase_values = [phase.attrib[x] for x in phase_attribs]
#                 row = plan_values + phase_values
#                 raw_timing_plan.append(row)
#     raw_timing_plan = pd.DataFrame(raw_timing_plan)
#     raw_timing_plan.columns = plan_attribs + phase_attribs
#     return raw_timing_plan

# def merge_yellow(raw_timing_plan):
#     timing_plan = []
#     row_attribs = ['id', 'type', 'programID', 'offset', 'duration', 'state']
#     last_row = None   
#     for index, row in raw_timing_plan.iterrows():
#         conditionA = last_row is not None
#         conditionB = 'y' in row['state']
#         if conditionA & conditionB:
#             # current phase yellow link index
#             yellow_link_index = [x[0] for x in list(enumerate(row['state'])) if x[1]=='y']
#             # corresponding link index's last phase stat
#             last_phase_stat = [x[1] for x in list(enumerate(last_row['state'])) if x[0] in yellow_link_index]
#             # all corresponding link index's last phase stat is g or G
#             conditionC = (sum(np.isin(last_phase_stat, ['g', 'G'])) == len(last_phase_stat))
#             if conditionC:
#                 duration = int(last_row['duration']) + int(row['duration'])
#                 merged_row = [last_row[x] for x in row_attribs[:4]] + [duration] + [last_row['state']]
#                 del timing_plan[-1]
#                 timing_plan.append(merged_row)
#             else:
#                 timing_plan.append(row.values)
#         else:
#             timing_plan.append(row.values)
#         last_row = row
#     timing_plan = pd.DataFrame(timing_plan)
#     timing_plan.columns = row_attribs
#     return timing_plan

def get_Lane_LinkIndex_relation(net_xml_root):
    relation = []
    cols =  ['from', 'to', 'fromLane', 'tl', 'linkIndex', 'dir']
    for r in net_xml_root:
        if (r.tag == 'connection') & ('linkIndex' in r.keys()):
            values = [r.attrib[x] for x in cols]
            relation.append(values)
    relation = pd.DataFrame(relation)
    relation.columns = cols
    return relation

def phase_listener(tlsID, previous_step_phase):
    # listen to phase change
    current_step_phase = traci.trafficlight.getRedYellowGreenState(tlsID)
    if current_step_phase != previous_step_phase:
        previous_step_phase = current_step_phase
        return 'phase changed !', previous_step_phase, current_step_phase
    else:
        return 'phase not changed !', previous_step_phase, current_step_phase

def get_current_phase_green_lanes(tlsID, current_phase, lane_linkIndex):
    # get green linkIndex:
    G_linkIndex = [str(x[0]) for x in enumerate(list(current_phase)) if (x[1] == 'g') | (x[1] == 'G')]
    # merge green linkIndex into green lane:
    bool_index = np.isin(lane_linkIndex['linkIndex'], G_linkIndex)
    G_edges = list(lane_linkIndex['from'].loc[bool_index])
    G_lanes = list(lane_linkIndex['fromLane'].loc[bool_index])
    # This will do all possible combination rather than pair paste: G_lanes = pd.unique([x+'_'+y for x in G_edges for y in G_lanes])
    # This is pair paste:
    G_lanes = [x[0]+'_'+x[1] for x in zip(G_edges, G_lanes)]
    G_lanes = set(G_lanes)
    return {tlsID:G_lanes}

def update_current_phase_lanes_flow(tlsID, phase_lanes_flow):
    # total waste for all lanes
    vacant_lanes_number = 0
    for GlaneID in phase_lanes_flow.keys():
        # lane's ID is the same as the induction detector ID on it
        step_data = traci.inductionloop.getVehicleData(GlaneID)
        if len(step_data) > 0:
            for vehicle_info in step_data:
                if vehicle_info[3] != -1:
                    phase_lanes_flow[GlaneID] += 1
        # if step_data == [], means no vehicle pass this detector
        else:
            vacant_lanes_number += 1
    return phase_lanes_flow, vacant_lanes_number
    
# set saturated flow for given lanes    
def set_lanes_SF(phase_lanes_flow, depend = 'default'):
    if depend == 'default':
        # default is 2000 veh/h
        return dict(zip(phase_lanes_flow.keys(), [2000]*len(phase_lanes_flow)))

def get_phase_lanes_efficiency(phase_state, phase_lanes_flow, phase_duration, lane_SF):
    phase_lanes_efficiency = []
    for lane in phase_lanes_flow.keys():
        lane_phase_flow = phase_lanes_flow[lane]/phase_duration*3600
        lane_saturated_flow = lane_SF[lane]
        efficiency = lane_phase_flow/lane_saturated_flow
        if efficiency > 1:
            efficiency = 1
        row = [lane, phase_duration, lane_phase_flow, lane_saturated_flow, efficiency]
        phase_lanes_efficiency.append(row)
    phase_lanes_efficiency = pd.DataFrame(phase_lanes_efficiency)
    phase_lanes_efficiency.columns = ['green_lanes_ID', 'phase_duration', 'lane_phase_flow', 'lane_SF', 'efficiency']
    return phase_lanes_efficiency
