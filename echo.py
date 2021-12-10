#!/usr/bin/env python3

import codecs
import socket
import socketserver

class EchoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # self.request is the TCP socket connected to the client
        while True:
            data = self.request.recv(1024)
            if not data:
                return
            s = data.decode("utf8")
            rot = codecs.encode(s, "rot13")
            self.request.sendall(rot.encode("utf8"))

class ThreadedEchoServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    address_family = socket.AF_INET6

if __name__ == "__main__":
    HOST, PORT = "::", 7777

    # Create the server, binding to localhost on port 9999
    with ThreadedEchoServer((HOST, PORT), EchoHandler) as server:
        server.serve_forever()
