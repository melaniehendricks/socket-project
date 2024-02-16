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


# infinite loop listening to given port for incoming messages from peers
while True:
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
            
            dict = eval(decoded)                                    # convert to dictionary and deconstruct
            command = dict["command"]
            peerName = dict["peer-name"]

            # peer wants to register 
            if command == "register":
                names = peerDict.keys()
                if peerName in names:                               # if name is not unique, FAILURE
                    sock.sendto("FAILURE", (peerIP, peerPort))
                else:
                    len = len(names)
                    peerDict[len] = {}
                    peerDict[len]["peer-name"] = peerName           # create peer element in dictionary
                    peerDict[len]["status"] = 'free'
                    sock.sendto(b"SUCCESS", (peerIP, peerPort))     # SUCCESS
                


