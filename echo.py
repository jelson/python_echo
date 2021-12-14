#!/usr/bin/env python3

import argparse
import cherrypy
import codecs
import datetime
import json
import psycopg2
import socket
import socketserver
import sys
import tabulate
import threading

from util import say, LOGFILE_NAME
import database

DEFAULT_PORT = 7777
MAGIC_HEADER = "magicheader"
DBNAME = "echostats"
TABLENAME = "receptions"

class ConnStats:
    def __init__(self):
        self.packets_received = set()
        self.total_packets = None
        self.total_length = 0
        self.nonce = None

    def receive(self, fields, data):
        if self.nonce:
            assert(self.nonce == fields['nonce'])
            assert(self.total_expected == fields['total_expected'])
        else:
            self.nonce = fields['nonce']
            self.total_expected = fields['total_expected']

        assert(fields['packet_num'] >= 0 and fields['packet_num'] < self.total_expected)

        if fields['packet_num'] not in self.packets_received:
            self.packets_received.add(fields['packet_num'])
            self.total_length += len(data)

        say(f"Nonce {self.nonce}: received {len(self.packets_received)}/{self.total_expected}, total {self.total_length} bytes")

class StatsCollector:
    def __init__(self):
        self.stats = {}
        self.db = database.DatabaseBatcher(DBNAME, TABLENAME)

    def receive(self, fields, data):
        nonce = fields['nonce']

        if nonce not in self.stats:
            self.stats[nonce] = ConnStats()

        self.stats[nonce].receive(fields, data)

        del fields['magic']
        self.db.insert(fields)

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

            self.request.sendall(self.server.process(self.client_address, data, debugstr))

class UDPEchoHandler(socketserver.DatagramRequestHandler):
    def handle(self):
        debugstr = f"{self.client_address} UDP datagram"

        data = self.rfile.read(100000)
        self.wfile.write(self.server.process(self.client_address, data, debugstr))

class ServerBaseMixIn:
    stats = StatsCollector()

    def parse_magic_header(self, s, data, debugstr):
        if len(s) > len(MAGIC_HEADER) and s[0:len(MAGIC_HEADER)] == MAGIC_HEADER:
            magic_header = s.split('\n')[0]
            fields = dict(zip(
                ['magic', 'nonce', 'packet_num', 'total_expected'],
                magic_header.split(':')))
            for numeric in ['packet_num', 'total_expected']:
                fields[numeric] = int(fields[numeric])
            fields['payload_len'] = len(data)
            say(f"{debugstr}: got magic header: {json.dumps(fields)}")
            fields['time'] = datetime.datetime.now()
            return fields
        else:
            return None

    def process(self, client_address, data, debugstr):
        say(f"{debugstr}: received {len(data)} bytes")
        s = data.decode("utf8", errors='ignore')

        # check and see if this is a packet with metadata that let us compute
        # statistics
        try:
            fields = self.parse_magic_header(s, data, debugstr)
            if fields:
                fields['address'] = str(client_address)
                self.stats.receive(fields, data)

        except Exception as e:
            say(f"couldn't process packet: {e}")
            raise e

        # return rot13'd
        rot = codecs.encode(s, "rot13")
        return rot.encode("utf8")

class ThreadedTCPEchoServer(socketserver.ThreadingMixIn, socketserver.TCPServer, ServerBaseMixIn):
    allow_reuse_address = True
    address_family = socket.AF_INET6
    debugstr = "TCP echo server"

class ThreadedUDPEchoServer(socketserver.ThreadingMixIn, socketserver.UDPServer, ServerBaseMixIn):
    allow_reuse_address = True
    address_family = socket.AF_INET6
    debugstr = "UDP echo server"

class Runner(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server

    def run(self):
        say(f"Starting {self.server.debugstr} on port {self.server.server_address}")
        self.server.serve_forever()

class EchoWebHandler():
    def __init__(self):
        self.db = psycopg2.connect(database=DBNAME)

    @cherrypy.expose
    def log(self):
        return "<pre>" + open(LOGFILE_NAME).read()

    @cherrypy.expose
    def summary(self):
        style = """
           <html>
           <head>
               <link rel="stylesheet" href="/echo-static/table.css">
           </head>
        """

        stmt = """
            SELECT
               nonce AS "Nonce",
               MIN(address) AS "IP Addr",
               MIN("time") AS "First Packet",
               MAX("time") AS "Last Packet",
               MAX(total_expected) AS "Packets Expected",
               COUNT(DISTINCT(packet_num)) AS "Unique Packets Received",
               COUNT(*) AS "Received Incl. Duplicates"
            FROM receptions
            GROUP BY nonce
            ORDER BY "First Packet" desc;
        """
        cursor = self.db.cursor()
        cursor.execute(stmt)
        result = cursor.fetchall()
        self.db.commit()
        return style + tabulate.tabulate(
            result,
            tablefmt='html',
            headers=[desc[0] for desc in cursor.description],
        )

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port', '-p',
        help='Port number',
        action='store',
        type=int,
        default=DEFAULT_PORT,
    )
    return parser.parse_args(sys.argv[1:])

if __name__ == "__main__":
    args = get_args()

    tcp = Runner(ThreadedTCPEchoServer(('::', args.port), TCPEchoHandler))
    tcp.start()

    udp = Runner(ThreadedUDPEchoServer(('::', args.port), UDPEchoHandler))
    udp.start()

    cherrypy.config.update({
        'server.socket_host': '::',
        'server.socket_port': args.port - DEFAULT_PORT + 16000,
        'server.socket_timeout': 30,
    })
    cherrypy.quickstart(EchoWebHandler(), script_name='/echo')
