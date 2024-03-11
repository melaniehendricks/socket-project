#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import sys          # keyboard input
import json         # json objects
import math
import random

# ./manager.py --port 7501 

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()

    global peerDict, sock, names, ports, DHT_complete, DHT_rebuilt, leaving_peer                          # global vars

    # assign arguments to variables
    mgrIP = "0.0.0.0"
    mgrPort = args.port
    group = 13
    DHT_complete = False
    DHT_rebuilt = ""
    leaving_peer = ""
                                           

    # packet variables
    #responseDict = {}
    names = []
    ports = []
    peerDict = {}                                           # store peer-name/state

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


    # infinite loop listening to given port for incoming messages from peers
    while True:
        events = selector.select()
        for key, _ in events:
            sockToRead = key.fileobj
            #data = sockToRead

            # ============ K E Y B O A R D    I N P U T =======================
            if key.fd == sys.stdin.fileno():
                msg = sys.stdin.readline()
                print("message from keyboard: %s" % msg)
            
            # ============ P E E R   S O C K E T  =======================
            if key.fd == sock.fileno():
                divider()
                msg, addr = sockToRead.recvfrom(1024)
                decoded = msg.decode('utf-8')
                peerIP, peerPort = addr
                #print(decoded)

                dict = eval(decoded)                                    # convert to dictionary and deconstruct
                print("received: %s\n" %dict)
                command = dict.get("command")

                peerName = dict.get("peer-name")
                if DHT_rebuilt == False:
                    if leaving_peer != peerName:
                        failureMsg(command, "DHT not yet rebuilt", peerIP, pmPort)  # if DHT NOT rebuilt yet
                        break
                    else:
                        if command == "dht-rebuilt":
                            DHT_rebuilt = True                  # ?????????????? "" or True
                            print("DHT has been rebuilt.\n")
                            updatePeers(command, dict, peerName)
                                                                  
                                               


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
                    strN = dict.get("n")
                    n = int(strN)
                    if n < 3:
                        failureMsg(command, "n is too small", peerIP, peer["m-port"])
                        break
                    if peerName not in names:
                        failureMsg(command, "name not registered", peerIP, peer["m-port"])
                        break
                    if len(names) < 3:
                        failureMsg(command, "not enough peers registered", peerIP, peer["m-port"])
                        break
                    if DHT_complete:
                        failureMsg(command, "DHT already exists", peerIP, peer["m-port"])
                        break
                    else:
                        peer = getPeer(peerName)
                        setupDHT(peer, n, command)
                        break

                # peer says DHT complete
                if command == "DHTcomplete":
                    peer = getPeer(peerName)
                    state = peer["state"]
                    if state != "leader":
                        failureMsg(command, "peer is not leader", peerIP, peer["m-port"])
                        break
                    else:
                        DHTComplete(peer, command)                        
                        break

                # peer wants to query DHT
                if command == "queryDHT":
                    if peerName not in names:
                        failureMsg(command, "peer not registered", peerIP, peerPort)
                        break
                    if DHT_complete is False:
                        print(DHT_complete)
                        failureMsg(command, "DHT setup not complete", peerIP, peer["m-port"])
                        break
                    peer = getPeer(peerName)
                    state = peer["state"]
                    if state != "free":
                        failureMsg(command, "peer is registered but not free", peerIP, peer["m-port"])
                        break
                    else:
                        peer = getPeer(peerName)
                        queryDHT(peerName, peer, command)
                    
                # peer wants to leave DHT
                if command == "leaveDHT":
                    #global leaving_peer
                    leaving_peer = peerName
                    DHT_rebuilt = False
                    print("Waiting for DHT to be rebuilt ......\n")
                    peer = getPeer(peerName)
                    if DHT_complete is False:
                        failureMsg(command, "DHT does not exist", peerIP, peer["m-port"])
                        break                    
                    state = peer["state"]
                    if state == "free":
                        failureMsg(command, "peer is not maintaining the DHT", peerIP, peer["m-port"])
                        break
                    else:
                        awaitRebuild(peer, command)
                


                        

# ============= HELPER METHODS ==========================
def divider():
    print("============================================================")

def failureMsg(command, reason, peerIP, port):
    responseDict = {}
    responseDict["return-code"] = "FAILURE"
    responseDict["command"] = command
    responseDict["reason"] = reason
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peerIP, port))
    print("response: %s\n" %jsonData)


def createPeer(name, port, pmPort, IP, command):
    length = len(names)
    peerDict[length] = {}
    peerDict[length]["peer-name"] = name                                # create peer element in dictionary
    peerDict[length]["state"] = 'free'
    peerDict[length]["p-port"] = port
    peerDict[length]["m-port"] = pmPort
    peerDict[length]["IP"] = IP
    names.append(name)
    print(peerDict)
    responseDict = {"return-code" : "SUCCESS!", "command": command}
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (IP, pmPort))
    print("response: %s\n" %jsonData)
    print("sent to %s on port %d\n" %(name, pmPort))


def getPeer(name):
    for i in range(0, len(peerDict)):
        if peerDict[i].get("peer-name") == name:
            return peerDict[i]


def setupDHT(peer, n, command):
    responseDict = {}
    responseDict["return-code"] = "SUCCESS"
    responseDict["command"] = command
    peerCount = 0                                                       # add leader to responseDict


    for i in range(0, n):
        responseDict[i] = {}
        
    peer["state"] = "leader"                                            # change state to "leader"
    reason = "** state of " + peer["peer-name"] + " is set to " + peer["state"] + " **"
    responseDict["reason"] = reason
    responseDict[peerCount]["peer-name"] = peer["peer-name"]
    responseDict[peerCount]["IP"] = peer["IP"]
    responseDict[peerCount]["p-port"] = peer["p-port"]
    #print(peerDict)
    for i in range(n):                                                  # add other peers to responseDict
        if peerDict[i].get("state") == "free" and peerCount < n-1:      
            peerCount += 1
            IP = peerDict[i].get("IP")                                  # get IP
            pPort = peerDict[i].get("p-port")                           # get peer port
            peerDict[i]["state"] = "inDHT"                              # change state to "inDHT"
            responseDict[peerCount]["peer-name"] = peerDict[i].get("peer-name")
            responseDict[peerCount]["IP"] = IP
            responseDict[peerCount]["p-port"] = pPort
        else:
            continue
    #print("check peerDict")
    #print(peerDict)
    responseDict["n"] = n
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peer["IP"], peer["m-port"]))
    print("response: %s\n" %jsonData)
    print("sent to %s on port %d\n" %(peer["peer-name"], peer["m-port"]))


def DHTComplete(peer, command): 
    global DHT_complete
    DHT_complete = True
    print("setting DHT_complete to %s\n" %DHT_complete)
    responseDict = {}
    responseDict["return-code"] = "SUCCESS"
    responseDict["command"] = command
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peer["IP"], peer["m-port"]))
    print("response: %s" %jsonData)
    print("sent to %s on port %d\n" %(peer["peer-name"], peer["m-port"]))


def queryDHT(name, peer, command):
    print("check state")
    print(peer)
    responseDict = {}
    responseDict["return-code"] = "SUCCESS"
    responseDict["command"] = command

    rand = random.randint(0, len(names) - 1)                        # find random peer in DHT
    returnPeer = peerDict[rand]
    while returnPeer["peer-name"] == name:
        rand = random.randint(0, len(names) - 1)
        returnPeer = peerDict[rand]

    responseDict["peer-name"] = returnPeer["peer-name"]
    responseDict["IP"] = returnPeer["IP"]
    responseDict["p-port"] = returnPeer["p-port"]
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peer["IP"], peer["m-port"]))
    print("response: %s" %jsonData)
    print("sent to %s on port %d\n" %(peer["peer-name"], peer["m-port"]))


def awaitRebuild(peer, command):
    responseDict = {}
    responseDict["return-code"] = "SUCCESS"
    responseDict["command"] = command
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peer["IP"], peer["m-port"]))
    print("response: %s" %jsonData)
    print("sent to %s on port %d\n" %(peer["peer-name"], peer["m-port"]))
    

def updatePeers(command, dict, peerName):
    peer = getPeer(peerName)
    peer["state"] = "free"                                                  # update state of leaving-peer to free
    print("state of %s is set to %s" %(peerName, peer["state"]))

    for item in peerDict:                                                   # update state of former leader to inDHT
        p = peerDict.get(item)
        if p["state"] == "leader":
            p["state"] = "inDHT"
            print("state of %s is set to %s" %(p["peer-name"], p["state"]))
            break

    l = dict["new-leader"]
    leader = getPeer(l)
    leader["state"] = "leader"                                              # update state of new leader
    print("state of %s is set to %s\n" %(l, leader["state"]))

    responseDict = {}
    responseDict["return-code"] = "SUCCESS"
    responseDict["command"] = command
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peer["IP"], peer["m-port"]))              # send leaving-peer response
    print("response: %s" %jsonData)
    print("sent to %s on port %d\n" %(peerName, peer["m-port"]))

main()