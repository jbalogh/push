from argparse import ArgumentParser
from functools import partial
import socket

from pyramid.path import DottedNameResolver
import tornado.ioloop
import tornado.web
import tornado.websocket
import zmq
from zmq.eventloop import ioloop, zmqstream

from mozsvc.config import load_into_settings


SOCKETS = {}
CONNECTIONS = 0


class SocketHandler(tornado.websocket.WebSocketHandler):
    token = None

    def open(self):
        global CONNECTIONS
        CONNECTIONS += 1

    def on_message(self, message):
        if message.startswith('token: '):
            self.token = message.split(' ', 1)[-1]
            SOCKETS[self.token] = self

    def on_close(self):
        global CONNECTIONS
        CONNECTIONS -= 1
        if self.token and self.token in SOCKETS:
            del SOCKETS[self.token]


application = tornado.web.Application([
    ('.*', SocketHandler),
])


class Push(object):

    def __init__(self, stream):
        stream.on_recv(self.recv)

    def recv(self, msg):
        key, token, data = msg
        self.send(token, data)

    def send(self, token, data):
        if token in SOCKETS:
            try:
                SOCKETS[token].write_message(data)
            except Exception:
                del SOCKETS[token]


def report_status(storage, ip):
    storage.add_edge_node(ip, CONNECTIONS)


def main():
    parser = ArgumentParser('Pubsub listener pushing to websockets.')
    parser.add_argument('config', help='path to the config file')
    args, settings = parser.parse_args(), {}
    load_into_settings(args.config, settings)
    config = settings['config']

    ioloop.install()
    sub_socket = zmq.Context().socket(zmq.SUB)
    sub_socket.connect(config.get('zeromq', 'sub'))
    sub_socket.setsockopt(zmq.SUBSCRIBE, 'PUSH')
    print 'SUB sub_socket on', config.get('zeromq', 'sub')

    loop = ioloop.IOLoop.instance()
    port = config.get('websockets', 'port')
    Push(zmqstream.ZMQStream(sub_socket, loop))
    application.listen(port)
    print 'websockets on :%s' % port

    # Send a status report every 10 seconds.
    cfg = config.get_map('storage')
    storage = DottedNameResolver(None).resolve(cfg.pop('backend'))(**cfg)
    ip = '%s:%s' % (socket.gethostbyname(socket.getfqdn()), port)
    callback = partial(report_status, storage, ip)

    period = config.get('monitor', 'period')
    ioloop.PeriodicCallback(callback, period * 1000).start()
    # Get in the pool right away.
    callback()

    loop.start()


if __name__ == '__main__':
    main()
