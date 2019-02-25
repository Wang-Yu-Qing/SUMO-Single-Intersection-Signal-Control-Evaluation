import numpy as np
def queue_quota(LanesQueueRatio):
    # quota for each lane:
    eq = 100/len(LanesQueueRatio)
    quota = 0
    for k, v in LanesQueueRatio.items():
        eq = eq - eq*(v**1.5)
        quota += eq
    return quota

def efficiency_quota(vacant_lanes_number, green_lanes_number):
    quota = 100 - 100*(vacant_lanes_number/green_lanes_number)
    return quota
    
def travel_quota(edges_travel_time, edges_mean_length=300, edges_free_flow_speed=60):
    """
    edges_mean_length: meter
    edges_free_flow_speed: KM/H
    """
    edges_mean_travel_time = np.mean(list(edges_travel_time.values()))/3600 # convert to hour
    quota = 100*((edges_mean_length/1000)/edges_free_flow_speed)/edges_mean_travel_time
    return quota

def emission_quota():
    pass

def quota_fusing(quotas, weights = 'equal'):
    quota = 0
    if weights == 'equal':
        weights = [1/len(quotas)] * len(quotas)
    for q, w in zip(quotas, weights):
        quota += q*w
    return quota