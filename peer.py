#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import math         # for math library
import random
import sys
import json

parser = argparse.ArgumentParser()

# add arguments for manager-ip, group, manager-port
parser.add_argument("--m-ip", required=True, type=str)        # IP not sanitized
parser.add_argument("--group", required=True, type=int)
parser.add_argument("--m-port", required=True, type=int)
parser.add_argument("--p-port", type=int)

args = parser.parse_args()

# assign arguments to variables
mgrIP = args.m_ip
peerIP = "127.0.0.1"
group = args.group
mgrPort = args.m_port
peerPort = args.p_port

# packet variables
commandDict = {}
names = ["cousin", "bear", "sugar", "faq", "ayo"]
len = len(names) - 1

# calc port range based on group
portMin = (math.ceil(group/2) * 1000) + 500
portMax = (math.ceil(group/2) * 1000) + 999

MESSAGE = b"Hello, World"
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

selector = selectors.DefaultSelector()
selector.register(sock, selectors.EVENT_READ)           # register sockets to listen to
selector.register(sys.stdin, selectors.EVENT_READ)      # register stdin to listen for


# bind to valid port
if peerPort:
    if peerPort >= portMin and peerPort <= portMax:
        try:
            sock.bind((peerIP, peerPort))
        except:
            "invalid port"
else:
    for p in range(portMin, portMax):
        try:
            sock.bind((peerIP, p))
            print("successful bind to port %d" % sock.getsockname)
        except:
            "failure to bind to port"

sock.sendto(MESSAGE, (mgrIP, mgrPort))
print("UDP target IP: %s" % mgrIP)
print("UDP target port: %d" % mgrPort)
print("message: %s" % MESSAGE)

# infinite loop listening to given port incoming messages from peers
while True:
    events = selector.select()
    for key, _ in events:
        sockToRead = key.fileobj
        data = sockToRead

        if key.fd == sys.stdin.fileno():
            #msg = input("")
            msg = sys.stdin.readline()
            if int(msg) == 1:                                   # register()
                # build dictionary to send
                rand = random.randint(0,len)
                commandDict["command"] = "register"
                commandDict["peer-name"] = names[rand]
                commandDict["IPv4-address"] = peerIP
                commandDict["m-port"] = mgrPort
                commandDict["p-port"] = peerPort
                names.pop(rand)
                jsonData = json.dumps(commandDict)
                sock.sendto(jsonData.encode(), (mgrIP, mgrPort))
                print("json sent to manager")
        
        if key.fd == sock.fileno():
            msg, addr = sockToRead.recvfrom(1024)
            print("message from socket: %s" % msg)


