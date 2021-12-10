#!/usr/bin/env python3

import codecs
import socket
import socketserver
import sys
import threading

PORT = 7777

def say(s):
    print(s)
    sys.stdout.flush()

def process(data, debugstr):
    say(f"{debugstr}: received {len(data)} bytes")
    s = data.decode("utf8", errors='ignore')
    rot = codecs.encode(s, "rot13")
    return rot.encode("utf8")


class TCPEchoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # self.request is the TCP socket connected to the client
        debugstr = f"{self.client_address}"
        say(f"{debugstr}: new tcp connection")

        while True:
            data = self.request.recv(4096)

            if not data:
                say(f"{debugstr}: closed")
                return

            self.request.sendall(process(data, debugstr))

class ThreadedTCPEchoServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    address_family = socket.AF_INET6
    debugstr = "TCP echo server"

class UDPEchoHandler(socketserver.DatagramRequestHandler):
    def handle(self):
        # self.request is the TCP socket connected to the client
        debugstr = f"{self.client_address} UDP datagram"

        data = self.rfile.read(100000)
        self.wfile.write(process(data, debugstr))

class ThreadedUDPEchoServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    allow_reuse_address = True
    address_family = socket.AF_INET6
    debugstr = "UDP echo server"

class Runner(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server

    def run(self):
        say(f"Starting {self.server.debugstr}")
        self.server.serve_forever()

if __name__ == "__main__":
    tcp = Runner(ThreadedTCPEchoServer(('::', PORT), TCPEchoHandler))
    tcp.start()

    udp = Runner(ThreadedUDPEchoServer(('::', PORT), UDPEchoHandler))
    udp.start()
