# Demo of Messager class.
# run with: DEVICE_ID=1 python sample.py
import os
import time
from clustermessaging.Messager import Messager

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
