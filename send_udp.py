#!/usr/bin/env python3

NUM_PACKETS=100
NUM_REPEATS=3
PACKET_LEN=1400

import socket
import time
import random

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

nonce = f"cmdline-exp-{time.time()}"

for cnt in range(NUM_REPEATS):
   for i in range(NUM_PACKETS):
       header = f"magicheader:{nonce}:{i}:{NUM_PACKETS}\n"
       payload_len = PACKET_LEN - len(header)
       payload = "".join([str(random.randrange(0, 10)) for i in range(payload_len)])
       data = (header + payload).encode('utf-8')
       sock.sendto(data, ("www.megabozo.com", 7777))
