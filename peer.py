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

    global mgrIP, peerIP, mgrPort, peerPort, peer_mgrPort, pSock, mSock, peerName, id, YYYY, rNeighbor, myDHT, s, records, startingPeer, fields      # global vars
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
    myDHT = {}
    fields = ""

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
                msg = sys.stdin.readline()
                if int(msg) == 1:                                   # register()
                    userInput = input("Enter peer name, peer address: \n")
                    vals = userInput.split(", ")
                    global peerName
                    peerName = vals[0]
                    address = vals[1]
                    #mport = vals[2]            # !!!!!!!!!!!! are these last 2 necessary since manager port is passed initially and peer port is generated immediately?
                    #pport = vals[3]
                    register(address, peer_mgrPort, peerPort)
                    break
                if int(msg) == 2:                                   # setup-DHT()
                    userInput = input("Enter n and year (YYYY): \n")
                    vals = userInput.split(", ")
                    n = vals[0]
                    global YYYY
                    YYYY = vals[1]
                    setup_DHT(n)
                if int(msg) == 3:                                   # constructDHTs()
                    constructDHTs()
                if int(msg) == 4:                                   # DHTcomplete() 
                    DHTcomplete()
                if int(msg) == 5:                                   # queryDHT()
                    queryDHT()
                if int(msg) == 6:                                   # beginQuery()
                    eventId = input("Enter event ID: \n")
                    beginQuery(startingPeer, eventId)


            
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
                        print(dict["reason"])
                        DHTp2p(dict)
                    if command == "DHTcomplete":
                        print("received: %s" %code)
                    if command == "queryDHT":
                        print("received: %s\n" %code)
                        startingPeer.append(dict["peer-name"])
                        startingPeer.append(dict["IP"])
                        startingPeer.append(dict["p-port"])
                        
                    
            # if peer socket
            if key.fd == pSock.fileno():
                msg, addr = sockToRead.recvfrom(1024)
                decoded = msg.decode("utf-8")
                dict = eval(decoded)
                command = dict["command"]
                if command == "set-id":                             # set-id()
                    global id
                    id = dict.get("id")
                    if id == 0:
                        print("logical ring setup complete")
                    if id != 0:
                        print("command received: %s\n" %command)
                        print("id: %d\n" %id)    
                        setId(dict, id)
                if command == "store":                              # store()
                    eid = dict.get("id")
                    pos = dict["pos"]
                    row = dict["event"]
                    s = dict["table-size"]
                    if eid == id:
                        match(pos, row)
                    else:
                        store(eid, s, pos, row)
                if command == "findEvent":                          # findEvent()
                    print("command received: %s\n" %dict["command"])
                    print("from port %d" %addr[1])
                    findEvent(dict)
                    






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

# failure + reason why
def parseFailureResponse(dict):
    command = dict["command"]               
    reason = dict["reason"]
    print("%s failed because %s. Please try again.\n" %(command,reason))

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
    

def setup_DHT(n):
    # build dictionary to send
    commandDict = {}
    commandDict["command"] = "setupDHT"
    commandDict["peer-name"] = peerName
    commandDict["n"] = n
    commandDict["YYYY"] = YYYY                                          
    jsonData = json.dumps(commandDict)
    print("\nsent: %s" %jsonData)
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
    ringSize = dict["n"]
    print("ring size: %s" %ringSize)
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
            index += 1

    i = 0 
    for peer in peers.values():
        if id == ringSize-1:                                #  peer n-1
            if i == 0:    
                # change nextId to leader      
                nextId = 0
                commandDict["id"] = nextId
                IP = peer["IP"]
                port = peer["p-port"]
                name = peer["peer-name"]
                rNeighbor.append(IP)
                rNeighbor.append(port)
                rNeighbor.append(name)
                break
        if i == nextId:                                  # leader + other peers
            #print(peer)
            commandDict["id"] = nextId
            IP = peer.get("IP")
            port = peer.get("p-port")
            name = peer["peer-name"]
            rNeighbor.append(IP)
            rNeighbor.append(port)
            rNeighbor.append(name)
            break
        i += 1

    print("right neighbor: %s\n" %peer)
    
    # build commandDict, update it with peers
    commandDict["command"] = "set-id"
    commandDict["n"] = ringSize
    commandDict.update(peers)                                
    jsonData = json.dumps(commandDict)
    print("\nsent: %s" %jsonData)
    print("to %s at %d\n" %(rNeighbor[0], rNeighbor[1]))
    pSock.sendto(jsonData.encode(), (rNeighbor[0], rNeighbor[1]))

    
def constructDHTs():
    fileName = "data/details-" + str(YYYY) + ".csv"
    rows = []
    with open(fileName, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        # returns current row (1st row)
        fields = next(reader)
        
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
        if eid == id:                                               # if id matches peer, store locally
            match(pos, row, fields)
        else:
            store(eid, s, pos, row)                                 # else, pass to right neighbor
        print('\n')
            

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
    

def store(id, s, pos, row):
    commandDict = {}
    commandDict["command"] = "store"                        # send store() to right neighbor with:
    commandDict["id"] = id                                  # id
    commandDict["table-size"] = s                           # table size
    commandDict["pos"] = pos                                # position at which to store event
    commandDict["event"] = row                              # event
    jsonData = json.dumps(commandDict)
    print("passing along to right neighbor: %s\n" %rNeighbor[2])
    print("sent: %s" %jsonData)
    print("to %s at %d\n" %(rNeighbor[0], rNeighbor[1]))
    pSock.sendto(jsonData.encode(), (rNeighbor[0], rNeighbor[1]))

def match(pos, row, header):
    print("stored event locally at position %d" %pos)
    print(row)
    global fields 
    fields = header
    global myDHT
    myDHT[pos] = {}
    myDHT[pos] = row                                        # store event in myDHT at position pos
    global records
    records += 1                                            # increment num records stored in peer
    print("num records: %d\n" %records)


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
    commandDict["event-id"] = eventId
    commandDict["S"] = peer
    commandDict["id-seq"] = []
    commandDict["I"] = []
    jsonData = json.dumps(commandDict)
    pSock.sendto(jsonData.encode(), (peer[1], peer[2]))
    print("\nsent %s" % jsonData)



def findEvent(dict):                               
    print(dict)
    ids = dict["I"]
    if len(ids) == 0:                                       # if peer == starting peer
        identifiers = []
        for i in range(ringSize - 1):
            identifiers.append(i)
        ids = identifiers

    eventId = dict["event-id"]
    pos = int(eventId) % s
    print("position: %d" %pos)
    #print(myDHT)
    eid = pos % ringSize
    if id == eid:                                           # if id matches
        #if myDHT.has_key(pos):
        event = myDHT.get(pos)
        print(event)
        if event[0] == eventId:                             # AND eventId matches
            print("event: %s" %event[0])
            print("eventId: %s" %eventId)
            commandDict = {}
            commandDict["return-code"] = "SUCCESS"          # return SUCCESS
            commandDict["event"] = event                    # + event
            commandDict["id-seq"] = id                      # + id sequence
            print("found event!")
            returnPeer = dict["S"]
            if peerName == returnPeer[0]:
                print(fields)
                # START HERE !!!!!!!!!!!!!!!!!!!!!!


    else:                                                   # if id does not match: hot potato
        ids.remove(id)                                      # remove peer id from list of remaining identifiers
        seq = dict["id-seq"]
        seq.append(str(id) + peerName)
        rand = random.randint(0, len(ids)-1)
        print(rand)
        next = ids[rand]
        print("next: %d" %next)


main()