#!/usr/bin/python3

import socket       # for sockets
import argparse     # to parse cmd line args
import selectors    # selectors module to handle multiple events
import sys          # keyboard input
import json         # json objects

parser = argparse.ArgumentParser()
parser.add_argument("--port", required=True, type=int, choices=range(7500,7999))
args = parser.parse_args()

mgrIP = "127.0.0.1"
mgrPort = args.port
peerDict = {}                                           # store peer-name/state

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

selector = selectors.DefaultSelector()
selector.register(sock, selectors.EVENT_READ)           # register sockets to listen to
selector.register(sys.stdin, selectors.EVENT_READ)      # register stdin to listen for

print("attempting to bind to %s on port" % mgrIP, mgrPort)
sock.bind((mgrIP, mgrPort))
print("bind successful")


# infinite loop listening to given port incoming messages from peers
while True:
    # parse json
    # get command
    # if command == register: register(peer-name, IP, m-port, p-port)
    events = selector.select()
    for key, _ in events:
        sockToRead = key.fileobj
        data = sockToRead

        if key.fd == sys.stdin.fileno():
            #msg = input("")
            msg = sys.stdin.readline()
            print("message from keyboard: %s" % msg)
        
        if key.fd == sock.fileno():
            msg, addr = sockToRead.recvfrom(1024)
            decoded = msg.decode('utf-8')
            peerIP, peerPort = addr
            
            dict = eval(decoded)                        # convert to dictionary
            command = dict["command"]
            peerName = dict["peer-name"]
            if command == "register":
                names = peerDict.keys()
                if peerName in names:
                    sock.sendto("FAILURE", (peerIP, peerPort))
                else:
                    status = {"status":"free"}
                    peerDict[peerName].append(status)
                    print("%s added.  Status: %s" % peerName, peerDict[peerName]["status"])
                    sock.sendto("SUCCESS")
                

            #print("received message: %s" % data)
            
            sock.sendto(b"POOOOP", (peerIP, peerPort))



#def register(peer-name, IP, m-port, p-port):
    # store peer-name, IP, 2 ports
    # state of peer = free
    
    # if peer-name and p-port is unique, send back "SUCCESS"
    # else send back "FAILURE"

#def setupDHT(peer-name, n, year):
