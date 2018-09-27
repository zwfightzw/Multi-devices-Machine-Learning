# Demo of Messager class.
# run with: DEVICE_ID=1 python sample.py
import os
import time
from clustermessaging.Messager import Messager
# change the parameter of DEVICE_ID based on special device num.
os.environ['DEVICE_ID'] = '1'

m = Messager()

def callback(message, name):
    print('Message Received from %s! %s' % (name, message))

if os.environ['DEVICE_ID'] == '1':
    print('registering callback')
    m.registerCallback(callback)
else:
    print('sending message')
    m.sendMessage('1', 'hello, 1, i am %s' % m.getOwnName())

m.start()
num = 0

if not os.environ['DEVICE_ID'] == '1':
    for i in range(10):
        m.sendMessage('1', 'hello, 1, i am %s, the num is %d'  % (m.getOwnName(),num))
        num = num + 1
