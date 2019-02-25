import socket as sk
import json
import numpy

s = sk.socket()
#host = sk.gethostname()
host = '10.10.50.23'
port = 5888
s.bind((host, port))

s.listen(5)
print('hosting on {}:{}'.format(host, port))

while True:
    print('listening...')
    c, addr = s.accept() # listening
    print('connected client IP: {}'.format(addr))
    c.send('connected!'.encode('utf-8'))
    while True:
        values = list(numpy.random.random(5))
        values = [str(x) for x in values]
        keys = ["a", "b", "c", "d", "e"]
        message = dict(zip(keys, values))
        message = json.dumps(message)
        try:
            c.sendall(message.encode('utf-8'))
        except:
            break # connection terminated by client, break current loop and keep listening
