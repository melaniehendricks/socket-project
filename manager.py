#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import sys          # keyboard input
import json         # json objects
import math

# ./manager.py --port 7501 

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--m-ip", required=True, type=str)
    parser.add_argument("--group", required=True, type=int)
    args = parser.parse_args()

    global responseDict, peerDict, sock, names, ports, DHTdict                           # global vars

    # assign arguments to variables
    mgrIP = "0.0.0.0"
    mgrPort = args.port
    group = 13
    DHT_flag = False
                                           

    # packet variables
    responseDict = {}
    names = []
    ports = []
    peerDict = {}                                           # store peer-name/state
    DHTdict = {}

    # calc port range based on group
    portMin = (math.ceil(group/2) * 1000) + 500
    portMax = (math.ceil(group/2) * 1000) + 999

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    selector = selectors.DefaultSelector()
    selector.register(sock, selectors.EVENT_READ)           # register sockets to listen to
    selector.register(sys.stdin, selectors.EVENT_READ)      # register stdin to listen for

    # bind to valid port
    if mgrPort is not None:
        if mgrPort >= portMin and mgrPort <= portMax:
            try:
                sock.bind((mgrIP, mgrPort))
                print("successful bind to port %d" % mgrPort)
                print("on %s" %mgrIP)
            except:
                sys.exit("Error: failure to bind")
        else:
            sys.exit("Error: please enter a valid port")

    # else: required=True => error: the following arguments are required: --port


    # infinite loop listening to given port for incoming messages from peers
    while True:
        events = selector.select()
        for key, _ in events:
            sockToRead = key.fileobj
            data = sockToRead

            # if keyboard input
            if key.fd == sys.stdin.fileno():
                msg = sys.stdin.readline()
                print("message from keyboard: %s" % msg)
            
            # if socket
            if key.fd == sock.fileno():
                msg, addr = sockToRead.recvfrom(1024)
                decoded = msg.decode('utf-8')
                peerIP, peerPort = addr
                #print(decoded)
                
                dict = eval(decoded)                                    # convert to dictionary and deconstruct
                print("received: %s" %dict)
                command = dict.get("command")
                peerName = dict.get("peer-name")

                # peer wants to register 
                if command == "register":
                    pmPort = dict.get("m-port")
                    print(command)
                    if peerName in names:                                   # if name is not unique, FAILURE
                        failureMsg(command, "name", peerIP, pmPort)
                        break
                    if peerPort in ports:                                   # if port is not unique, FAILURE
                        failureMsg(command, "port", peerIP, pmPort)           
                        break
                    else:
                        createPeer(peerName, peerPort, pmPort, peerIP, command)
                        break
                # peer wants to setup DHT
                if command == "setupDHT":
                    peer = getPeer(peerName)
                    n = dict.get("n")
                    if n < 3:
                        failureMsg(command, "n is too small", peerIP, peer["m-port"])
                    if peerName not in names:
                        failureMsg(command, "name not registered", peerIP, peer["m-port"])
                    if len(names) < 3:
                        failureMsg(command, "not enough peers registered", peerIP, peer["m-port"])
                    if DHT_flag:
                        failureMsg(command, "DHT already exists", peerIP, peer["m-port"])
                    else:
                        setupDHT(peer, n, command)
                        

# ============= HELPER METHODS ==========================
                
def failureMsg(command, reason, peerIP, port):
    responseDict["return-code"] = "FAILURE"
    responseDict["command"] = command
    responseDict["reason"] = reason
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peerIP, port))
    print("response: %s\n" %jsonData)

def createPeer(name, port, pmPort, IP, command):
    length = len(names)
    peerDict[length] = {}
    peerDict[length]["peer-name"] = name           # create peer element in dictionary
    peerDict[length]["state"] = 'free'
    peerDict[length]["p-port"] = port
    peerDict[length]["m-port"] = pmPort
    peerDict[length]["IP"] = IP
    names.append(name)
    #print(peerDict)
    responseDict = {"return-code" : "SUCCESS", "command": command}
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (IP, pmPort))
    print("response: %s" %jsonData)
    print("sent to port %d\n" %pmPort)

def getPeer(name):
    for i in range(0, len(peerDict)):
        if peerDict[i].get("peer-name") == name:
            return peerDict[i]

def setupDHT(peer, n, command):
    # select n-1 free users 
    # update users "state" = inDHT
    # return-code = SUCCESS + 
    # Dict of peers (n 3-tuples) to leader
    DHTdict["return-code"] = "SUCCESS"
    DHTdict["command"] = command
    peerCount = 0                                      # add leader to DHTdict
    DHTdict[peerCount] = {}
    peer["state"] = "leader"                          # change state to "leader"
    index = "peer" + str(peerCount)
    DHTdict[peerCount]["peer"] = index
    DHTdict[peerCount]["IP"] = peer["IP"]
    DHTdict[peerCount]["p-port"] = peer["p-port"]
    #print(peerDict)
    for i in range(1,n):                            # add other peers to DHTdict
        peerCount += 1
        if peerDict[i].get("state") == "free":      
            IP = peerDict[i].get("IP")              # get IP
            pPort = peerDict[i].get("p-port")       # get peer port
            peerDict[i]["state"] = "inDHT"          # change state to "inDHT"
            DHTdict[i] = {}
            index = "peer" + str(peerCount)
            DHTdict[i]["peer"] = index
            DHTdict[i]["IP"] = IP
            DHTdict[i]["p-port"] = pPort
    print(peerDict)
    jsonData = json.dumps(DHTdict)
    sock.sendto(jsonData.encode(), (peer["IP"], peer["m-port"]))
    print("response: %s" %jsonData)
    print("sent to port %d\n" %peer["m-port"])


main()