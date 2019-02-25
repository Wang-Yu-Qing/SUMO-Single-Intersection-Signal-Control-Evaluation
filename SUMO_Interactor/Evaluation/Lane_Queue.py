import xml.etree.ElementTree as et
import traci
import traci.constants as tc
import os
import numpy as np

def get_all_lanes_queue_ratio(all_laneareas_detec_ID, lanes_length):
    lanes_queue_ratio = {}
    for lanDetecID in all_laneareas_detec_ID:
        # get jam length:
        laneID = traci.lanearea.getLaneID(lanDetecID) # corresponding lane's ID
        lane_length = lanes_length[laneID] # corresponding lane's length
        queue_length = traci.lanearea.getJamLengthMeters(lanDetecID) # jam length
        queue_ratio = float(queue_length)/float(lane_length) # queue ratio
        lanes_queue_ratio[laneID] = queue_ratio
    return lanes_queue_ratio

def get_top_three_lane_queue_ratio(lanes_queue_ratio):
    sorted_lanes_queue_ratio = sorted(lanes_queue_ratio.items(), key = lambda x:x[1], reverse = True)
    return sorted_lanes_queue_ratio[:3]

def get_mean_lane_queue_ratio(lanes_queue_ratio):
    mean_lane_queue_ratio = np.mean(list(lanes_queue_ratio.values()))
    return mean_lane_queue_ratio