import os
import xml.etree.ElementTree as et

import pandas as pd


# get net.xml root:
def get_net_xml_root(cfgfile):
    if cfgfile.split('.')[-1] != 'cfg':
        print('PLEAS INPUT A sumo.cfg file')
        return False
    config_dir = os.path.dirname(cfgfile)
    tree = et.parse(cfgfile)
    root = tree.getroot()
    for elem in root:
        if elem.tag == 'input':
            netfilename = elem.find('n').attrib['v']
            break
    tree = et.parse(os.path.join(config_dir, netfilename))
    root = tree.getroot()
    return root

# get edge information via root of .net.xml
def get_all_edgesID(net_xml_root):
    all_edges = []
    for elem in net_xml_root:
       if (elem.tag == 'edge') & ('from' in elem.attrib.keys()):
           edgeID = elem.attrib['id']
           all_edges.append(edgeID)
    return all_edges

def get_all_lanes_length(net_xml_root):
    lanes_length = {}
    for elem in net_xml_root:
        if (elem.tag == 'edge') & ('from' in elem.attrib.keys()):
            lanes = elem.findall('lane')
            for lane in lanes:
                lanes_length[lane.attrib['id']] = lane.attrib['length'] 
    return lanes_length


# get all lanes' ID via root of net.xml file
def get_all_lanes_ID(net_xml_root):
    lanesID = []
    for elem in net_xml_root:
        if (elem.tag == 'edge') & ('from' in elem.attrib.keys()):
            lanes = elem.findall('lane')
            for l in lanes:
                lanesID.append(l.attrib['id'])
    return lanesID

# get all lanearea detectors' ID via cfg -> addition.xml file
def get_all_lanearea_detec_ID(cfgfile):
    # find addtional xml file path via cfg file:
    tree = et.parse(cfgfile)
    root = tree.getroot()
    input_ = root.find('input') # get all content in input
    for elem in input_:
        if elem.tag == 'additional-files':
            addfilename = elem.attrib['value']
            break
    config_dir = os.path.dirname(cfgfile)
    addfilepath = os.path.join(config_dir, addfilename)
    # find all lane area detectors ID in additional file:
    tree = et.parse(addfilepath)
    root = tree.getroot()
    lanearea_detecID = []
    for elem in root:
        if elem.tag == 'laneAreaDetector':
            lanearea_detecID.append(elem.attrib['id'])
    return lanearea_detecID

# get all induction loop detectors' ID via root of net.xml file
def get_all_induction_detec_ID(cfgfile):
    induction_detecID = []
    cfgfile_dir = os.path.dirname(cfgfile)
    tree = et.parse(cfgfile)
    root = tree.getroot()
    for elem in root:
        if elem.tag == 'input':
            addfilename = elem.find('additional-files').attrib['value']
            addfilepath = os.path.join(cfgfile_dir, addfilename)
            break
    tree = et.parse(addfilepath)
    root = tree.getroot()
    for elem in root:
        if elem.tag == 'instantInductionLoop':
            induction_detecID.append([elem.attrib['id'], elem.attrib['lane']])
    induction_detecID = pd.DataFrame(induction_detecID)
    induction_detecID.columns = ['id', 'lane']
    return induction_detecID
