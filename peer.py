#!/usr/bin/python3

import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--manager-port", required=True, type=int, choices=range(7500,7999))
# IP not sanitized
parser.add_argument("--manager-ip", required=True, type=str)
args = parser.parse_args()

UDP_IP = args.manager_ip
UDP_PORT = args.manager_port
MESSAGE = b"Hello, World"

print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %d" % UDP_PORT)
print("message: %s" % MESSAGE)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
