"""
Messages are passed from the API layer to the socket server layer through
pub/sub, but zmq pub/sub is limited to one publisher. We want pub/sub so that
each socket server can pass on messages for the users it's connected to.

Thus, we run routers in the middle that act listen to the API servers using
push/pull and send messages to the socket servers using pub/sub. The socket
servers can listen to a small list of publishing routers instead of every API
server.
"""
from argparse import ArgumentParser

import tornado.ioloop
import tornado.web
import tornado.websocket
import zmq
from zmq.eventloop import ioloop, zmqstream

from mozsvc.config import load_into_settings


class Proxy(object):

    def __init__(self, pull_stream, publish_stream):
        self.pull = pull_stream
        self.pub = publish_stream

        self.pull.on_recv(self.recv)

    def recv(self, msg):
        self.pub.send_multipart(msg)


def main():
    parser = ArgumentParser('Router to publish messages to edge nodes.')
    parser.add_argument('config', help='path to the config file')
    args, settings = parser.parse_args(), {}
    load_into_settings(args.config, settings)
    config = settings['config']

    ioloop.install()
    loop = ioloop.IOLoop.instance()

    context = zmq.Context()
    pull_socket = context.socket(zmq.PULL)
    pull_socket.connect(config.get('zeromq', 'pull'))
    pull_stream = zmqstream.ZMQStream(pull_socket, loop)
    print 'PULL socket on', config.get('zeromq', 'pull')

    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind(config.get('zeromq', 'pub'))
    pub_stream = zmqstream.ZMQStream(pub_socket, loop)
    print 'PUB socket on', config.get('zeromq', 'pub')

    Proxy(pull_stream, pub_stream)

    loop.start()


if __name__ == '__main__':
    main()
