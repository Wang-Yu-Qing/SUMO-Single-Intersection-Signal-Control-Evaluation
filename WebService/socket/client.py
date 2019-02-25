import socket as sk
import json

s = sk.socket()
#host = sk.gethostname()
host = '10.10.50.23'
port = 5888

s.connect((host, port))
while True:
    recieve = s.recv(1024)
    try:
        print(json.loads(recieve)) # only loads and print when there is data recieved
    except:
        continue
s.close()