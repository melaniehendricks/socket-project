#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import math         # for math library
import random
import sys
import json
import csv

# peer.py --m-ip 192.168.1.4 --m-port 7501 

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--m-ip", required=True, type=str)        # IP not sanitized
    parser.add_argument("--m-port", required=True, type=int)
    #parser.add_argument("--p-port", type=int)

    args = parser.parse_args()

    global mgrIP, peerIP, mgrPort, peerPort, peer_mgrPort, pSock, mSock, peerName                                # global vars
    global peers, id, ringSize, rNeighbor, myDHT, s, records, startingPeer, fields, lNeighbor, rebuildingDHT    
    global leader 
    ringSize = 0
    # assign arguments to variables
    mgrIP = args.m_ip
    peerIP = "0.0.0.0"
    group = 13
    mgrPort = args.m_port
    DHTflag = False
    s = 0
    records = 0
    startingPeer = []
    fields = ""
    rNeighbor = []
    lNeighbor = []    
    rebuildingDHT = False
    leader = []


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

            # ============ K E Y B O A R D    I N P U T =======================
            if key.fd == sys.stdin.fileno():
                divider()
                msg = sys.stdin.readline()
                if int(msg) == 0:
                    print(myDHT)

                if int(msg) == 1:                                       # register()
                    userInput = input("Enter peer name, peer address: \n")
                    vals = userInput.split(", ")
                    global peerName
                    peerName = vals[0]
                    address = vals[1]
                    #mport = vals[2]            # !!!!!!!!!!!! are these last 2 necessary since manager port is passed initially and peer port is generated immediately?
                    #pport = vals[3]
                    register(address, peer_mgrPort, peerPort)
                    break

                if int(msg) == 2:                                       # setup-DHT()
                    userInput = input("Enter n and year (YYYY): \n")
                    vals = userInput.split(", ")
                    n = vals[0]
                    #global YYYY
                    YYYY = vals[1]
                    setup_DHT(n, YYYY)

                if int(msg) == 3:                                       # constructDHTs()
                    constructDHTs(YYYY)

                if int(msg) == 4:                                       # DHTcomplete() 
                    DHTcomplete()

                if int(msg) == 5:                                       # queryDHT()
                    queryDHT()

                if int(msg) == 6:                                       # beginQuery()
                    eventId = input("Enter event ID: \n")
                    beginQuery(startingPeer, eventId)

                if int(msg) == 7:                                       # leaveDHT()
                    leaveDHT()

                if int(msg) == 8:                                       # teardown()
                    n = ringSize - 1
                    teardown(n, rNeighbor, "teardown")

                if int(msg) == 9:                                       # rebuildDHT()
                    year = input("Enter year (YYYY): \n")
                    rebuildDHT(year)

                if int(msg) == 10:                                      # joinDHT()
                    name = input("Enter name: \n")
                    joinDHT(name)

                if int(msg) == 11:                                      # initTeardown()                    
                    initTeardown(peerName)
                    



            
            # ============ M A N A G E R   S O C K E T =======================
            if key.fd == mSock.fileno():
                divider()
                msg, addr = sockToRead.recvfrom(1024)
                #print(msg)
                # decode msg + convert to Dictionary
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                #print(dict)
                code = dict["return-code"]
                if code == "FAILURE":                                   # failure 
                    print("received: %s\n" %code)     
                    parseFailureResponse(dict)
                else:                                                   # success
                    command = dict["command"]
                    if command == "register":
                        print("received: %s\n" %code)   

                    if command == "setupDHT":
                        print("received: %s\n" %code)
                        print(dict["reason"])
                        DHTp2p(dict)

                    if command == "DHTcomplete":
                        print("received: %s\n" %code)

                    if command == "queryDHT":
                        print("received: %s\n" %code)
                        startingPeer.append(dict["peer-name"])
                        startingPeer.append(dict["IP"])
                        startingPeer.append(dict["p-port"])

                    if command == "leaveDHT":
                        print("received: %s\n" %code)

                    if command == "dht-rebuilt":
                        print("received: %s\n" %code)

                    if command == "joinDHT":
                        print("received: %s" %code)
                        current = dict["leader"]
                        leader.append(current["peer-name"])
                        leader.append(current["IP"])
                        leader.append(current["p-port"])
                        print("current leader: %s\n" %leader)
                        
                    
            # ============ P E E R   S O C K E T  =======================
            if key.fd == pSock.fileno():
                divider()
                msg, addr = sockToRead.recvfrom(1024)
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                command = dict["command"]
                if command == "set-id":                                 # set-id
                    id = getId(dict)
                    print("id: %d" %id)

                    n = dict["size"]
                    count = dict["count"]
                    print("count: %d" %count)

                    if count == n:
                        print("logical ring setup complete")
                        divider()
                    else:
                        print("command received: %s\n" %command)
                        setId(dict, id, n, command, count)



                if command == "store":                                  # store
                    eid = dict.get("id")
                    pos = dict["pos"]
                    row = dict["event"]
                    s = dict["table-size"]
                    header = dict["header"]
                    if eid == id:
                        match(pos, row, header)
                    else:
                        store(eid, s, pos, row, header)



                if command == "findEvent":                              # findEvent
                    print("command received: %s\n" %command)
                    print("from port %d" %addr[1])
                    code = dict["return-code"]
                    if code == "FAILURE":                               # failure 
                        print("received: %s\n" %code)     
                        parseFailureResponse(dict)
                    else:
                        findEvent(dict)



                if command == "foundEvent":                             # foundEvent
                    print("command received: %s\n" %command)
                    foundEvent(fields, dict["event"], dict["id-seq"])



                if command == "teardown":                               # teardown
                    print("command received: %s" %command)
                    fromPeer = dict["peer-name"]
                    print("from %s\n" %fromPeer)

                    delDHT()
                    n = dict["count"]
                    print("count: %d" %n)
                    if n == ringSize - 1:
                        savePeerToNotify(addr, dict, "DHT complete")                # need to notify when DHT rebuilt

                    if n == 0:                                      # if leaving-peer
                        print("back to peer who initiated")

                        newPeers = reorderPeersLeaving(peers, id)   # reorder peers
                        id = -1                                     # set new id
                        newSize = ringSize - 1                      # set new ring size
                        setId(newPeers, -1, newSize, "reset-id", -1)
                    else:
                        n = n - 1
                        teardown(n, rNeighbor, "teardown") 



                if command == "reset-id":                                 # reset-id
                    id = getId(dict)

                    size = dict["size"]
                    count = dict["count"]
                    print("count: %d" %count)
                    print("id: %d\n" %id)
                    if count == 0:                                     # if new leader
                        print("** new leader of DHT **")
                        setId(dict, id, size, command, count)
                    elif count == size:                                 # if leaving-peer
                        print("logical ring setup complete")
                        divider()
                    else:
                        print("command received: %s\n" %command)
                        setId(dict, id, size, command, count)



                if command == "rebuild-dht":                            # rebuild-dht
                    print("command received: %s" %command)
                    year = dict["YYYY"]
                    rebuildingDHT = True
                    constructDHTs(year)



                if command == "dht-rebuilt":                            # dht-rebuilt
                    print("command received: %s" %command)
                    manager = []
                    manager.append("manager")
                    manager.append(mgrIP)
                    manager.append(mgrPort)
                    dhtRebuilt(manager, rNeighbor[0])                   # leaving-peer alerts manager



                if command == "teardown-join":                          # teardown-join
                    print("command received: %s" %command)
                    fromPeer = dict["peer-name"]
                    print("from %s\n" %fromPeer)

                    delDHT()
                    n = dict["count"]
                    print("count: %d" %n)

                    if n == 0:                               # if current leader
                        savePeerToNotify(addr, dict, "teardown complete")
                        dict.pop("peer-name")

                    if n == ringSize:
                        print("back to leader")
                        reorderPeersJoining(peers, lNeighbor)
                        break

                    teardown(n+1, rNeighbor, "teardown-join")

                    






# ============= HELPER METHODS ==========================

def bindToPorts(group, socket):                                         # calc port range based on group
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


def parseFailureResponse(dict):                                          # failure + reason why
    command = dict["command"]               
    reason = dict["reason"]
    print("%s failed because %s. \n" %(command,reason))


def divider():
    print("============================================================")

def register(address, mport, pport):
    # build dictionary to send
    commandDict = {}
    global peerName
    commandDict["command"] = "register"
    commandDict["peer-name"] = peerName
    commandDict["IPv4-address"] = address
    commandDict["m-port"] = mport
    commandDict["p-port"] = pport
    jsonData = json.dumps(commandDict)
    print("\nsent: %s\n" %jsonData)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))
    

def setup_DHT(n, YYYY):
    # build dictionary to send
    commandDict = {}
    commandDict["command"] = "setupDHT"
    commandDict["peer-name"] = peerName
    commandDict["n"] = n
    commandDict["YYYY"] = YYYY                                          
    jsonData = json.dumps(commandDict)
    print("\nsent: %s" %jsonData)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))


def DHTp2p(dict):                                                      # pop items and begin ring setup
    dict.pop("return-code")
    dict.pop("command")
    global id
    id = 0
    n = dict["n"]
    setId(dict, id, n, "set-id", 0)
    


def setId(dict, id, n, command, count):
    global myDHT
    myDHT = {}                                                  # initialize DHTs,
    global rNeighbor                                            # right neighbor,
    commandDict = {}
    global peers
    peers = {}                                                  # peers,
    global ringSize
    ringSize = n                                                # and ring size

    nextId = id+1
    print("ring size: %s" %ringSize)

    index = 0
    count += 1

    if command == "set-id":                                     # SET-ID ===============================
        for item in dict:                                       # save peers in ring
            if item.isdigit() or type(item) is int:
                peers[index] = {}
                peer = dict.get(item)
                peers[index] = peer
                index += 1

        i = 0
        for peer in peers.values():
            if id == ringSize-1:                                    #  peer n-1
                if i == 0:    
                    # change nextId to leader      
                    nextId = 0
                    commandDict["id"] = nextId
                    IP = peer["IP"]
                    port = peer["p-port"]
                    name = peer["peer-name"]
                    rNeighbor = []
                    rNeighbor.append(name)
                    rNeighbor.append(IP)                            # get caboose's right neighbor (leader)
                    rNeighbor.append(port)
                    break
            if i == nextId:                                         # leader + other peers
                commandDict["id"] = nextId
                IP = peer["IP"]
                port = peer["p-port"]
                name = peer["peer-name"]
                rNeighbor = []
                rNeighbor.append(name)
                rNeighbor.append(IP)                                # get right neighbor
                rNeighbor.append(port)
                break
            i += 1
    
    else:                                                       # RESET-ID =================================
        if count > 0:
            dict.pop("id")                                      # remove extraneous data 
            dict.pop("command")
            dict.pop("size")
            dict.pop("count")
        peers = dict                                            # reassign peers 
        commandDict["id"] = nextId

        if id == ringSize - 1:                                  # if caboose, reassign right neighbor
            peer = peers["0"]
            name = peer["peer-name"]
            IP = peer["IP"]
            port = peer["p-port"]

            oldRight = rNeighbor
            rNeighbor = []
            rNeighbor.append(name)
            rNeighbor.append(IP)
            rNeighbor.append(port)
            print("right neighbor: %s\n" %rNeighbor)

            commandDict["command"] = command                            # build commandDict, update it with peers
            commandDict["size"] = ringSize
            commandDict["count"] = count
            commandDict.update(peers)                                
            jsonData = json.dumps(commandDict)
            print("\nsent: %s" %jsonData)
            print("to %s\n" %(oldRight[0]))
            pSock.sendto(jsonData.encode(), (oldRight[1], oldRight[2])) # send to leaving-peer
            return


    print("right neighbor: %s\n" %rNeighbor)

    
    commandDict["command"] = command                            # build commandDict, update it with peers
    commandDict["size"] = ringSize
    commandDict["count"] = count
    commandDict.update(peers)                                
    jsonData = json.dumps(commandDict)
    print("\nsent: %s" %jsonData)
    print("to %s\n" %(rNeighbor[0]))
    pSock.sendto(jsonData.encode(), (rNeighbor[1], rNeighbor[2]))

    
def getId(dict):
    global id
    id = dict["id"]
    return id
    

def constructDHTs(YYYY):
    #global myDHT
    #myDHT = {}
    fileName = "data/details-" + str(YYYY) + ".csv"
    rows = []
    with open(fileName, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        fields = next(reader)                                   # returns current row (fields)
        
        for row in reader:                                      # extract data
            rows.append(row)
        l = reader.line_num - 1

        print(l)
        global s
        s = 2*l + 1
        prime = isPrime(s)                                      # find next prime after 2*l

        while prime == False:
            s += 1
            prime = isPrime(s)    
        #print(s)

    for row in rows:
        print(row)
        eventId = int(row[0])
        pos = eventId % s
        eid = pos % ringSize
        if eid == id:                                           # if id matches peer, store locally
            match(pos, row, fields)
        else:
            store(eid, s, pos, row, fields)                     # else, pass to right neighbor
        print('\n')

    print("Reached end of records.\n")
    
    if rebuildingDHT is True:                                   # new leader alerts leaving-peer
        dhtRebuilt(lNeighbor, "")

            

def isPrime(s):
    if s > 1:
        # iterate from 2 to s / 2 ================= change to sqrt??
        for i in range(2, int(s/2)+1):

            # if s is divisible by any # between 2 and s / 2: not prime
            if (s % i) == 0:
                return False
        return True
    else:
        return False
    

def store(id, s, pos, row, header):
    commandDict = {}
    commandDict["command"] = "store"                        # send store() to right neighbor with:
    commandDict["id"] = id                                  # id
    commandDict["table-size"] = s                           # table size
    commandDict["pos"] = pos                                # position at which to store event
    commandDict["event"] = row                              # event
    commandDict["header"] = header
    jsonData = json.dumps(commandDict)
    print("passing along to right neighbor: %s\n" %rNeighbor[0])
    print("sent: %s" %jsonData)
    print("to %s at %d\n" %(rNeighbor[1], rNeighbor[2]))
    pSock.sendto(jsonData.encode(), (rNeighbor[1], rNeighbor[2]))

def match(pos, row, header):
    print("stored event locally at position %d" %pos)
    print(row)
    global fields 
    fields = header
    global myDHT
    myDHT[pos] = {}
    myDHT[pos] = row                                        # store event in myDHT at position pos
    #global records
    #records += 1                                            # increment num records stored in peer
    print("num records: %d\n" %len(myDHT))


def DHTcomplete():                                          # send to manager
    commandDict = {}
    commandDict["command"] = "DHTcomplete"
    commandDict["peer-name"] = peerName
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))
    print("\nsent %s" %jsonData)


def queryDHT():                                             # send to manager
    commandDict = {}
    commandDict["command"] = "queryDHT"
    commandDict["peer-name"] = peerName
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))
    print("\nsent %s" %jsonData)


def beginQuery(peer, eventId):                              # send findEvent() to starting peer, S
    print("starting peer S: %s at %s:%d\n" %(peer[0], peer[1], peer[2]))
    commandDict = {}
    commandDict["command"] = "findEvent"
    commandDict["return-code"] = "pending"
    commandDict["event-id"] = eventId
    commandDict["S"] = peer
    commandDict["id-seq"] = []
    commandDict["I"] = []
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (peer[1], peer[2]))
    print("\nsent %s\n" % jsonData)



def findEvent(dict):                               
    print(dict)
    print("\n")
    ids = dict["I"]
    idSeq = dict["id-seq"]
    returnPeer = dict["S"]
    eventId = dict["event-id"]

    if len(ids) == 0:                                                                   # if peer == starting peer
        identifiers = []
        for i in range(ringSize):
            identifiers.append(i)
        ids = identifiers
    #print("ids: %s" %ids)    

    ids.remove(id)
    pos = int(eventId) % s
    print("Looking for: %s\n" %eventId)
    #print("position: %d" %pos)
    eid = pos % ringSize
    idSeq.append(str(id) + ":" + peerName)

    if id == eid:                                                                       # if id matches      
        print("id == eid")  
        event = myDHT.get(pos)       
        if event == None:                                                               # but no event, hot potato
            print("no event")
            hotPotato(ids, eventId, returnPeer, idSeq)

        elif event[0] == eventId:                                                       # AND eventId matches
            print("FOUND EVENT!\n")            
            if peerName == returnPeer[0]:                                               # if peer == starting peer                
                foundEvent(fields, event, idSeq)

            else:                                                                       # otherwise, send to starting peer
                print("Sending event to starting peer: %s" %returnPeer)
                commandDict = {}
                commandDict["return-code"] = "SUCCESS"                                  # return SUCCESS
                commandDict["command"] = "foundEvent"
                commandDict["event"] = event                                            # + event
                commandDict["id-seq"] = idSeq                                           # + id sequence
                jsonData = json.dumps(commandDict)
                pSock.sendto(jsonData.encode(), (returnPeer[1], returnPeer[2]))
                print("\nsent %s\n" %jsonData)
                print("to %s at %d" % (returnPeer[1], returnPeer[2]))
        else:
            hotPotato(ids, eventId, returnPeer, idSeq)
                
    else:                                                                               # if id does not match: hot potato     
        print("id != eid")
        if len(ids) == 0:
            if len(idSeq) == ringSize:                                                  # if no more peers to query
                print("no more peers")
                eventNotFound(returnPeer, eventId)
                return
        hotPotato(ids, eventId, returnPeer, idSeq)


def hotPotato(ids, eventId, returnPeer, idSeq):
    print("Event not found. HOT POTATO!")

    rand = random.randint(0, len(ids)-1)
    next = ids[rand]                                                                    # choose who to pass eventId to
    nextPeer = peers[next]
    print("Passing to: %s\n" %nextPeer)

    commandDict = {}
    commandDict["command"] = "findEvent"
    commandDict["return-code"] = "pending"
    commandDict["event-id"] = eventId
    commandDict["S"] = returnPeer
    commandDict["id-seq"] = idSeq
    commandDict["I"] = ids
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (nextPeer['IP'], nextPeer['p-port']))
    print("\nsent %s\n" %jsonData)
    print("to %s at %d" % (nextPeer["peer-name"],nextPeer["p-port"]))


def foundEvent(fields, event, idSeq):
    labeledEvent = zip(fields, event)
    for (f,e) in labeledEvent:
        print("%s: %s" %(f,e))
    print("=====================================")
    print(idSeq)
    print("")


def eventNotFound(returnPeer, eventId):
    if returnPeer[0] == peerName:
        print("queryDHT failed because storm event %s could not be found in the DHT. Please try again." %eventId)
        return
    else:
        commandDict = {}
        commandDict["return-code"] = "FAILURE"
        commandDict["command"] = "findEvent"
        commandDict["reason"] = "storm event %s could not be found in the DHT." %eventId
        jsonData = json.dumps(commandDict)
        pSock.sendto(jsonData.encode(), (returnPeer[1], returnPeer[2]))
        print("\nsent %s\n" %jsonData)
        print("to %s at %d" %(returnPeer[0],returnPeer[2]))


def leaveDHT():
    commandDict = {}
    commandDict["command"] = "leaveDHT"
    commandDict["peer-name"] = peerName
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))
    print("\nsent %s\n" %jsonData)


def teardown(n, recipient, command):
    commandDict = {}
    commandDict["command"] = command
    commandDict["count"] = n
    commandDict["peer-name"] = peerName
    jsonData = json.dumps(commandDict)
    print("passing along to right neighbor: %s\n" %recipient[0])
    pSock.sendto(jsonData.encode(), (recipient[1], recipient[2]))
    print("\nsent %s\n" %jsonData)


def savePeerToNotify(addr, dict, event):                                    # right neighbor of leaving-peer or peer wanting to join                  
    global lNeighbor
    lNeighbor = []
    lNeighbor.append(dict["peer-name"])
    lNeighbor.append(addr[0])
    lNeighbor.append(addr[1])
    print("peer to notify when %s: %s" %(event, lNeighbor))


def delDHT():
    global myDHT
    myDHT = {}


def reorderPeersLeaving(peers, id):
    newPeers = {}

    index = 0
    if id > 0 and id < ringSize - 1:                            # if leaving-peer is somewhere in the middle
        for i in range(id+1, ringSize):                         # add peers after leaving-peer
            peer = peers[i]
            newPeers[index] = {}
            newPeers[index] = peer
            index += 1
        
        for i in range(0, id):                                  # add peers before leaving-peer
            peer = peers[i]
            newPeers[index] = {}
            newPeers[index] = peer
            index += 1

    elif id == 0:                                               # if leaving-peer is leader
        for i in range(id+1, ringSize):                         # add only peers after leaving-peer
            peer = peers[i]
            newPeers[index] = {}
            newPeers[index] = peer
            index += 1

    else:                                                       # if leaving-peer is last
        for i in range(ringSize):
            peer = peers[i]
            newPeers[index] = {}
            newPeers[index] = peer
            index += 1

    return newPeers



def rebuildDHT(year):
    commandDict = {}
    commandDict["command"] = "rebuild-dht"
    commandDict["YYYY"] = year
    jsonData = json.dumps(commandDict)
    print("sent: %s" %jsonData)
    print("to %s\n" %rNeighbor[0])
    pSock.sendto(jsonData.encode(), (rNeighbor[1], rNeighbor[2]))


def dhtRebuilt(receiver, optional):
    commandDict = {}
    commandDict["command"] = "dht-rebuilt"
    commandDict["peer-name"] = peerName
    commandDict["new-leader"] = optional
    jsonData = json.dumps(commandDict)
    print("sent: %s" %jsonData)
    print("to %s\n" %(receiver[0]))
    pSock.sendto(jsonData.encode(), (receiver[1], receiver[2]))


def joinDHT(name):                                                          # joining-peer sends to manager
    commandDict = {}
    commandDict["command"] = "joinDHT"
    commandDict["peer-name"] = name
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (mgrIP, mgrPort))
    print("\nsent %s" %jsonData)
    print("to manager\n")
    

def initTeardown(name):                                                     # joining-peer sends to leader
    commandDict = {}
    commandDict["command"] = "teardown-join"
    commandDict["peer-name"] = name
    commandDict["count"] = 0
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (leader[1], leader[2]))
    print("\nsent: %s" %jsonData)
    print("to %s\n" %leader[0])


def reorderPeersJoining(peers, joiner):                                     # leader reorders peers
    print(joiner)
    print("peers before joiner: %s\n" %peers)

    newP = {}
    newP["peer-name"] = joiner[0]
    newP["IP"] = joiner[1]
    newP["p-port"] = joiner[2]

    newPeers = {}
    newPeers[0] = {}
    newPeers[0] = newP

    for i in range(0, ringSize):
        newPeers[i+1] = {}
        newPeers[i+1] = peers[i]

    print("peers after joiner: %s\n" %newPeers)
    return newPeers

main()