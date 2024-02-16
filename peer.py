#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import math         # for math library
import random
import sys
import json


def main():
    parser = argparse.ArgumentParser()

    # peer.py --m-ip 192.168.1.4 --group 13 --m-port 7501 --p-ip 0.0.0.0

    # add arguments for manager-ip, group, manager-port
    parser.add_argument("--m-ip", required=True, type=str)        # IP not sanitized
    parser.add_argument("--group", required=True, type=int)
    parser.add_argument("--m-port", required=True, type=int)
    parser.add_argument("--p-ip", required=True, type=str)
    parser.add_argument("--p-port", type=int)

    args = parser.parse_args()

    # assign arguments to variables
    global mgrIP, peerIP, mgrPort, peerPort, peer_mgrPort, commandDict, names, sock       # global vars
    mgrIP = args.m_ip
    peerIP = args.p_ip
    group = args.group
    mgrPort = args.m_port
    peerPort = args.p_port
    peer_mgrPort = 0                # fix this

    # packet variables
    commandDict = {}
    names = ["cousin", "bear", "sugar", "faq", "ayo"]

    # calc port range based on group
    portMin = (math.ceil(group/2) * 1000) + 500
    portMax = (math.ceil(group/2) * 1000) + 999

    MESSAGE = b""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    selector = selectors.DefaultSelector()
    selector.register(sock, selectors.EVENT_READ)           # register sockets to listen to
    selector.register(sys.stdin, selectors.EVENT_READ)      # register stdin to listen for

    # bind to valid port
    if peerPort is not None:
        if peerPort >= portMin and peerPort <= portMax:
            try:
                sock.bind((peerIP, peerPort))
                print("successful bind to port %d" % peerPort)
                print("on %s" %peerIP)
            except:
                sys.exit("Error: failure to bind")
        else:
            sys.exit("Error: please enter a valid port")
    else:
        for p in range(portMin, portMax+1):
            try:
                print("attempting to bind to %d" %p)
                sock.bind((peerIP, p))
                ip, pt = sock.getsockname()
                if pt >= portMin and pt <= portMax:
                    print("successful bind to port %d" % pt)
                    peerPort = pt
                    break           
            except:
                sys.exit("Error: failure to bind to any port")

            
    # infinite loop listening to given port incoming messages from peers
    while True:
        events = selector.select()
        for key, _ in events:
            sockToRead = key.fileobj
            data = sockToRead

            # if keyboard input
            if key.fd == sys.stdin.fileno():
                #msg = input("")
                msg = sys.stdin.readline()
                if int(msg) == 1:                                   # register()
                    register()
            
            # if socket
            if key.fd == sock.fileno():
                msg, addr = sockToRead.recvfrom(1024)
                print(msg)
                # parse msg
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                #print(decoded)
                code = dict["return-code"]
                if code == "FAILURE":
                    command = decoded["command"]
                    reason = decoded["reason"]
                    if command == "register":
                        if reason == "name":
                            register()


def register():
    # build dictionary to send
    rand = random.randint(0,len(names) - 1)
    commandDict["command"] = "register"
    commandDict["peer-name"] = names[rand]
    commandDict["IPv4-address"] = peerIP
    commandDict["m-port"] = mgrPort
    commandDict["p-port"] = peerPort
    names.pop(rand)
    jsonData = json.dumps(commandDict)
    #print(jsonData)
    sock.sendto(jsonData.encode(), (mgrIP, mgrPort))

main()