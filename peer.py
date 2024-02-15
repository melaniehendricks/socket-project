#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import math         # for math library
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

# calc port range based on group
portMin = (math.ceil(group/2) * 1000) + 500
portMax = (math.ceil(group/2) * 1000) + 999

MESSAGE = b"Hello, World"
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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
    data, addr = sock.recvfrom(1024)
    print("received message: %s" % data)

