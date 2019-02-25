import requests
from time import sleep

address = 'http://10.10.50.23:5555/'

# init url:
initi = 'init/afse'
# trigger url:
trigger = 'trigger/' 
# phases flow url:
phases_flow = 'get_data_cycle_phases_flow/'




requests.post(address+initi)
while True:
    sleep(0.2)
    t = requests.post(address+trigger)
    print(t.text)
    p = requests.post(address+phases_flow)
    print(p.text)