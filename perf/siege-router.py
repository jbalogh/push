#!/usr/bin/env python
"""
Measures the throughput of router.py. This script creates:

    1. A process to send data into the router with a zmq.PUSH socket.
    2. A process to receive data from the router with a zmq.SUB socket.

Processes are created with multiprocessing so there's no explicit interaction,
though there could still be implicit interaction through shared CPU resources.

My results for one sender and receiver:
    ** Average Sent Rate: 196,853 messages per second **
    ** Average Received Rate: 6,918 messages per second **
"""
from argparse import ArgumentParser
from multiprocessing import Process
import threading
import time

import zmq


class Stat(object):

    def __init__(self, kind, limit, rate=5):
        self.kind = kind
        self.limit = limit
        self.rate = rate

        self.start = time.time()
        self.count = 0
        self.prev_time = time.time()
        self.prev_count = 0

    def render(self):
        now, count = time.time(), self.count
        elapsed = now - self.prev_time
        diff = count - self.prev_count
        print '%s: %s (+%s %.2f/s)' % (self.kind, count,
                                       diff, float(diff) / elapsed)
        print 'Time: %.2f' % (now - self.start)
        print
        self.prev_time = now
        self.prev_count = count

    def printer(self):
        counter = 0
        while self.count < self.limit:
            counter += 1
            if counter % self.rate == 0:
                self.render()
            time.sleep(1)

    def __enter__(self):
        self.thread = threading.Thread(target=self.printer)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.render()
        self.thread.join()
        t = self.end - self.start
        print '** Average %s Rate: %.2f/s **\n' % (self.kind,
                                                   float(self.count) / t)


def sender(limit, push_addr):
    context = zmq.Context()
    push_socket = context.socket(zmq.PUSH)
    push_socket.connect(push_addr)

    with Stat('Sent', limit) as stat:
        msg = ('SIEGE', 'token', 'data')
        start = time.time()
        while stat.count < limit:
            push_socket.send_multipart(msg)
            stat.count += 1
        stat.end = time.time()


def receiver(limit, sub_addr):
    context = zmq.Context()
    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect(sub_addr)
    sub_socket.setsockopt(zmq.SUBSCRIBE, 'SIEGE')

    with Stat('Received', limit, rate=20) as stat:
        while stat.count < limit:
            sub_socket.recv_multipart()
            stat.count += 1
        stat.end = time.time()


def main(limit, push_addr, sub_addr, num_senders, num_receivers):
    limit = int(limit)
    procs = []
    for _ in range(num_senders):
        procs.append(Process(target=sender,
                             args=(limit, push_addr)))
    for _ in range(num_receivers):
        procs.append(Process(target=receiver,
                             args=(limit * num_senders, sub_addr)))

    for p in procs:
        p.start()
    for p in procs:
        p.join()


if __name__ == '__main__':
    parser = ArgumentParser(description='Siege router.py')
    arg = parser.add_argument
    arg('limit', type=int,
        help='number of messages to send')
    arg('push_address',
        help='zeromq address to connect the PUSH socket')
    arg('subscribe_address',
        help='zeromq address to connect the SUB socket')
    arg('--senders', default=1, type=int,
        help='number of sending processes')
    arg('--receivers', default=1, type=int,
        help='number of receiving processes')
    args = parser.parse_args()
    main(args.limit, args.push_address, args.subscribe_address,
         args.senders, args.receivers)
