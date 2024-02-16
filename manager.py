#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import sys          # keyboard input
import json         # json objects
import math

# ./manager.py --port 7501 --m-ip 0.0.0.0 --group 13

def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--m-ip", required=True, type=str)
    parser.add_argument("--group", required=True, type=int)
    args = parser.parse_args()

    global responseDict, peerDict, sock, names, ports                           # global vars

    # assign arguments to variables
    mgrIP = args.m_ip
    mgrPort = args.port
    group = args.group
    peerDict = {}                                           # store peer-name/state

    # packet variables
    responseDict = {}
    names = []
    ports = []

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
                command = dict["command"]
                peerName = dict["peer-name"]

                # peer wants to register 
                if command == "register":
                    ports = []
                    #print(items)

                    if peerName in names:                                   # if name is not unique, FAILURE
                        failureMsg(command, "name", peerIP, peerPort)
                        break
                    if peerPort in ports:                                   # if port is not unique, FAILURE
                        failureMsg(command, "port", peerIP, peerPort)           
                        break
                    else:
                        length = len(names)
                        peerDict[length] = {}
                        peerDict[length]["peer-name"] = peerName           # create peer element in dictionary
                        peerDict[length]["status"] = 'free'
                        peerDict[length]["p-port"] = peerPort
                        names.append(peerName)
                        #print(peerDict)
                        responseDict = {"return-code" : "SUCCESS"}
                        jsonData = json.dumps(responseDict)
                        sock.sendto(jsonData.encode(), (peerIP, peerPort))
                        break

                
def failureMsg(command, reason, peerIP, peerPort):
    responseDict["return-code"] = "FAILURE"
    responseDict["command"] = command
    responseDict["reason"] = reason
    jsonData = json.dumps(responseDict)
    sock.sendto(jsonData.encode(), (peerIP, peerPort))


main()