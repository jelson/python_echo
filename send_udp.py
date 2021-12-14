#!/usr/bin/env python3

NUM_PACKETS=30
NUM_REPEATS=1
PACKET_LEN=1400
HOST='www.megabozo.com'
PORT=7777

import codecs
import random
import socket
import threading
import time

class Packet:
   def __init__(self, packetnum, data):
      self.packetnum = packetnum
      self.rawdata = data.encode("utf8")
      self.rotdata = codecs.encode(data, "rot13").encode("utf8")

      self.received = 0

class SenderReceiver:
   def __init__(self):
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.sock.bind(('', 0))
      self.nonce = f"cmdline-exp-{int(time.time())}"
      self.requests = self.build_requests()

   def build_requests(self):
      retval = []

      for i in range(NUM_PACKETS):
          header = f"magicheader:{self.nonce}:{i}:{NUM_PACKETS}\n"
          payload_len = PACKET_LEN - len(header)
          payload = "".join([str(random.randrange(0, 10)) for i in range(payload_len)])
          data = (header + payload)
          retval.append(Packet(i, data))

      return retval

   def receiver(self):
      while True:
         data, addr = self.sock.recvfrom(100000)

         which_received = None

         for p in self.requests:
            if data == p.rotdata:
               p.received += 1
               which_received = p.packetnum
               break

         if which_received is None:
            print("Got unknown packet!")
            continue

         num_received = 0
         for p in self.requests:
            if p.received > 0:
               num_received += 1

         print(f"Received packet {which_received}, now have {num_received}/{len(self.requests)}")

         if num_received == len(self.requests):
            return

   def send_all(self):
      to_send = self.requests.copy()

      for packet in to_send:
         for i in range(NUM_REPEATS):
            print(f"Sending packet {packet.packetnum}")
            time.sleep(0.001)
            self.sock.sendto(packet.rawdata, (HOST, PORT))

   def run(self):
      t = threading.Thread(target=self.receiver)
      t.start()
      self.send_all()
      t.join()


def main():
   sr = SenderReceiver()
   sr.run()

main()
