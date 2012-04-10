from argparse import ArgumentParser
import json
import urllib

import zmq
from zmq.eventloop import ioloop, zmqstream
from tornado import httpclient
from tornado.escape import utf8

from mozsvc.config import load_into_settings


class Push(object):

    def __init__(self, url, auth_key, stream):
        self.url = url
        self.stream = stream
        self.stream.on_recv(self.recv)
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': 'GoogleLogin auth=%s' % auth_key}

    def recv(self, msg):
        msg = ''.join(msg)
        self.send(*msg.split(' ', 2)[1:])

    def send(self, droid_id, data, collapse_key='c'):
        params = {'registration_id': utf8(droid_id),
                  'collapse_key': utf8(collapse_key)}
        for key, value in json.loads(data).items():
            params['data.' + utf8(key)] = utf8(value)
        body = urllib.urlencode(params)
        http = httpclient.AsyncHTTPClient()
        http.fetch(self.url, None, method='POST',
                   headers=self.headers, body=body)


def main():
    parser = ArgumentParser('Pubsub listener pushing to Android C2DM.')
    parser.add_argument('config', help='path to the config file')
    args, settings = parser.parse_args(), {}
    load_into_settings(args.config, settings)
    config = settings['config']

    ioloop.install()
    socket = zmq.Context().socket(zmq.SUB)
    socket.connect(config.get('zeromq', 'sub'))
    socket.setsockopt(zmq.SUBSCRIBE, 'PUSH')
    print 'listening on', config.get('zeromq', 'sub')

    loop = ioloop.IOLoop.instance()
    c2dm = config.get_map('c2dm')
    Push(c2dm['url'], c2dm['auth_key'], zmqstream.ZMQStream(socket, loop))
    loop.start()


if __name__ == '__main__':
    main()
