#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import math         # for math library
import random
import sys
import json

# peer.py --m-ip 192.168.1.4 --m-port 7501 

def main():
    parser = argparse.ArgumentParser()

    # add arguments for manager-ip, group, manager-port
    parser.add_argument("--m-ip", required=True, type=str)        # IP not sanitized
    #parser.add_argument("--group", required=True, type=int)
    parser.add_argument("--m-port", required=True, type=int)
    #parser.add_argument("--p-ip", required=True, type=str)
    parser.add_argument("--p-port", type=int)

    args = parser.parse_args()

    global mgrIP, peerIP, mgrPort, peerPort, peer_mgrPort, commandDict, names, pSock, mSock       # global vars
    
    # assign arguments to variables
    mgrIP = args.m_ip
    peerIP = "0.0.0.0"
    group = 13
    mgrPort = args.m_port
                                               # fix this ---------- sock.connect()

    # packet variables
    commandDict = {}
    names = ["cousin", "bear", "sugar", "faq", "ayo"]
    
    # bind to ports
    pSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peerPort = bindToPorts(group, pSock)
    peer_mgrPort = bindToPorts(group, mSock)

    selector = selectors.DefaultSelector()
    selector.register(pSock, selectors.EVENT_READ)           # register peer socket to listen to
    selector.register(mSock, selectors.EVENT_READ)           # register manager socket to listen to
    selector.register(sys.stdin, selectors.EVENT_READ)      # register stdin to listen for

            
    # infinite loop listening to given port incoming messages from peers
    while True:
        events = selector.select()
        for key, _ in events:
            #print(key)
            sockToRead = key.fileobj
            #print(sockToRead)
            data = sockToRead

            # if keyboard input
            if key.fd == sys.stdin.fileno():
                #msg = input("")
                msg = sys.stdin.readline()
                if int(msg) == 1:                                   # register()
                    register()
                    break
            
            # if manager socket
            if key.fd == mSock.fileno():
                msg, addr = sockToRead.recvfrom(1024)
                #print(msg)
                # decode msg + convert to Dictionary
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                #print(decoded)
                code = dict["return-code"]
                if code == "FAILURE":     
                    command = dict["command"]               
                    reason = dict["reason"]
                    print("%s failed due to invalid %s. Please try again." %(command,reason))
                else:
                    print("%s" %code)
                    print("test")
                    
            # if peer socket
            #if key.fd == pSock.fileno

def bindToPorts(group, socket):
    # calc port range based on group
    portMin = (math.ceil(group/2) * 1000) + 500
    portMax = (math.ceil(group/2) * 1000) + 999

    port = random.randint(portMin + 1, portMax + 1)
    print("attempting to bind to %d" %port)
    socket.bind((peerIP, port))
    didBind = socket.fileno()
    if didBind > -1:
        print("successful bind to port %d" %port)
    else:
        print("failure to bind to any port")
    return port



def register():
    # build dictionary to send
    rand = random.randint(0,len(names) - 1)
    commandDict["command"] = "register"
    commandDict["peer-name"] = names[rand]
    commandDict["IPv4-address"] = peerIP
    commandDict["m-port"] = peer_mgrPort
    commandDict["p-port"] = peerPort
    names.pop(rand)
    jsonData = json.dumps(commandDict)
    #print(jsonData)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))

main()