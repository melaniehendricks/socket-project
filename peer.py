#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import math         # for math library
import random
import sys
import json

# peer.py --m-ip 192.168.1.4 --m-port 7501 
peerName = "peer"

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--m-ip", required=True, type=str)        # IP not sanitized
    parser.add_argument("--m-port", required=True, type=int)
    #parser.add_argument("--p-port", type=int)

    args = parser.parse_args()

    global mgrIP, peerIP, mgrPort, peerPort, peer_mgrPort, pSock, mSock, peerName, id, ringSize, rNeighbor       # global vars
    
    # assign arguments to variables
    mgrIP = args.m_ip
    peerIP = "0.0.0.0"
    group = 13
    mgrPort = args.m_port
    DHTflag = False

    # packet variables
    
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
                if int(msg) == 2:                                   # setup-DHT()
                    setup_DHT()

            
            # if manager socket
            if key.fd == mSock.fileno():
                msg, addr = sockToRead.recvfrom(1024)
                #print(msg)
                # decode msg + convert to Dictionary
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                #print(dict)
                code = dict["return-code"]
                if code == "FAILURE":                               # failure 
                    print("received: %s\n" %code)     
                    parseFailureResponse(dict)
                else:                                               # success
                    command = dict["command"]
                    if command == "register":
                        print("received: %s\n" %code)   
                    if command == "setupDHT":
                        print("received: %s\n" %code)
                        DHTp2p(dict)
                    
            # if peer socket
            if key.fd == pSock.fileno():
                msg, addr = sockToRead.recvfrom(1024)
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                command = dict["command"]
                print("command received: %s" %command)
                if command == "set-id":                             # set-id()
                    global id
                    id = dict.get("id")
                    print("id: %d\n" %id)    
                    if id != 0:
                        setId(dict, id)



# ============= HELPER METHODS ==========================

def bindToPorts(group, socket):
    # calc port range based on group
    portMin = (math.ceil(group/2) * 1000) + 500
    portMax = (math.ceil(group/2) * 1000) + 999

    port = random.randint(portMin + 1, portMax + 1)
    print("attempting to bind to %d" %port)
    socket.bind((peerIP, port))
    didBind = socket.fileno()
    if didBind > -1:
        print("successful bind to port %d\n" %port)
    else:
        print("failure to bind to any port")
    return port


def parseFailureResponse(dict):
    command = dict["command"]               
    reason = dict["reason"]
    print("%s failed because %s. Please try again.\n" %(command,reason))

def register():
    # build dictionary to send
    commandDict = {}
    rand = random.randint(0,100)
    global peerName
    peerName += str(rand)
    commandDict["command"] = "register"
    commandDict["peer-name"] = peerName
    commandDict["IPv4-address"] = peerIP
    commandDict["m-port"] = peer_mgrPort
    commandDict["p-port"] = peerPort
    jsonData = json.dumps(commandDict)
    print("sent: %s\n" %jsonData)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))
    

def setup_DHT():
    # build dictionary to send
    commandDict = {}
    commandDict["command"] = "setupDHT"
    commandDict["peer-name"] = peerName
    commandDict["n"] = 3
    commandDict["YYYY"] = 1950
    jsonData = json.dumps(commandDict)
    print("sent: %s" %jsonData)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))


def DHTp2p(dict):
    # pop items and begin ring setup
    dict.pop("return-code")
    dict.pop("command")
    global id
    id = 0
    setId(dict, id)
    


def setId(dict, id):
    nextId = id+1
    global ringSize
    ringSize = dict.get("n")
    global rNeighbor
    commandDict = {}
    rNeighbor = []
    peers = {}
    index = 0
    
    for item in dict:                                       # get peers
        if item.isdigit():
            peers[index] = {}
            peer = dict.get(item)
            peers[index] = peer
            #print(peer)
            index += 1

    i = 0 
    for peer in peers.values():
        if id == ringSize-1:                                #  caboose
            if i == 0:    
                print(peer)
                # change nextId to leader      
                nextId = 0
                commandDict["id"] = nextId
                IP = peer["IP"]
                port = peer["p-port"]
                rNeighbor.append(IP)
                rNeighbor.append(port)
                break
        if i == nextId:                                  # leader + others
            print(peer)
            commandDict["id"] = nextId
            IP = peer.get("IP")
            port = peer.get("p-port")
            rNeighbor.append(IP)
            rNeighbor.append(port)
            break
        i += 1

    print("right neighbor: %s\n" %rNeighbor)
    
    # build commandDict, update it with peers
    commandDict["command"] = "set-id"
    commandDict["n"] = ringSize
    commandDict.update(peers)                                
    jsonData = json.dumps(commandDict)
    print("sent: %s" %jsonData)
    print("to %s at %d\n" %(rNeighbor[0], rNeighbor[1]))
    pSock.sendto(jsonData.encode(), (rNeighbor[0], rNeighbor[1]))

    


main()