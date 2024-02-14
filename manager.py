#!/usr/bin/python3

import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--port", required=True, type=int, choices=range(7500,7999))
args = parser.parse_args()


UDP_IP = "127.0.0.1"
UDP_PORT = args.port

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("attempting to bind to %s" % UDP_IP)
print("on port %d" % UDP_PORT)
sock.bind((UDP_IP, UDP_PORT))
print("bind successful")



while True:
    data, addr = sock.recvfrom(1024)
    print("received message: %s" % data)
    for a in addr:
        print("from %s" % a)