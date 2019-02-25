from flask import Flask, render_template, request
from flask_cors import *
import os
import sys
import json
sys.path.append("..") # for importing SUMO_Interactor
sys.path.append("E:\\python_projects\\sumo\\SUMO_Interactor") # for importing Evaluation 
from SUMO_Interactor.SUMO_Interactor import SUMO_Interactor
import traci
import traci.constants as tc

app = Flask(__name__)
CORS(app, supports_credentials = True)

# define simulation generator
def simulation_generator():
    # only executed in first next() call
    global interactor
    interactor = SUMO_Interactor('E:\\python_projects\\sumo\\PlatServer_Interactor\\test.sumo.cfg')
    print('SUMO environment started!')
    while True:
        # one simulation step
        traci.simulationStep()
        # global object interactor will be updated
        interactor.vehicles()
        interactor.edges_lanes()
        interactor.phase_efficiency()
        interactor.computing_quota()
        interactor.step_finish()
        yield interactor.step # return stepID

#home page
@app.route('/')
def home():
    return '信号管控平台评价模块'

# init simulation via input intersection name
@app.route('/init/<intersection_name>', methods=['GET', 'POST'])
def init(intersection_name):
    # build network via intersection name:
    pass
    try:
        global generator
        # init generator meanwhile start SUMO simulation 
        generator = simulation_generator()
        return 'Initialization success!'
    except Exception as E:
        return E

# # restart the simulation
# @app.route('/restart', methods=['POST','GET'])
# def restart():
#     # close simulation
#     traci.close()
#     try:
#         global generator
#         generator = simulation_generator()
#         return 'generator restarted!'
#     except Exception as E:
#         return E

# trigger the simulation via generator
@app.route('/trigger/', methods=['GET', 'POST'])
def trigger():
    global generator
    stepID = next(generator)
    # return 'step:{}'.format(next(generator)) this is incorrect! making next(generator) called twice in one request!
    return str(stepID) # return the step ID

# ========================= define functions for geting data from global object interactor ============================
# edges travel time
@app.route('/get_data_edges_travel_time/', methods=['GET', 'POST'])
def get_data_edges_travel_time():
    global interactor
    message = json.dumps(interactor.edges_travel_time, ensure_ascii=False)
    return message

# phase efficiency
@app.route('/get_data_phase_efficiency/', methods=['GET', 'POST'])
def get_data_phase_efficiency():
    global interactor
    if hasattr(interactor, 'phase_lanes_efficiency'):
        # if object has attribute phase_lanes_efficiency
        message = json.dumps(dict(zip(interactor.phase_lanes_efficiency['green_lanes_ID'], interactor.phase_lanes_efficiency['efficiency'])), ensure_ascii=False)
        return message
    else:
        return json.dumps('None')

# phases flow within a cycle
@app.route('/get_data_cycle_phases_flow/', methods=['GET', 'POST'])
def get_data_cycle_phases_flow():
    global interactor
    if (interactor.current_phase_id==0) & (interactor.current_cycle_id>1):
        message = dict(zip(interactor.phases_id, interactor.phases_flow))
        return json.dumps(message, ensure_ascii=False)
    else:
        return json.dumps('cycle not finished !')

# step quota
@app.route('/get_data_step_quota/', methods=['GET', 'POST'])
def get_data_step_quota():
    global interactor
    message = json.dumps(interactor.step_quota)
    return message

# step total number of vehicles
@app.route('/get_data_number_of_vehicles/', methods=['GET', 'POST'])
def get_data_number_of_vehicles():
    global interactor
    message = json.dumps(len(interactor.VehIDs))
    return message

# end simulation
@app.route('/end/', methods=['GET', 'POST'])
def end_simulaton():
    traci.close()
    print('Simulation ended!')
    return 'Simulation ended!'

# export evaluation results
@app.route('/export_results/', methods=['GET', 'POST'])
def export_results():
    pass

if __name__ == '__main__':
    #HOST = environ.get('SERVER_HOST', 'localhost')
    HOST = '10.10.50.23'
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    # init global variables:
    interactor = None
    generator = None
    app.run(HOST, PORT)