from argparse import ArgumentParser
from functools import partial
import time

from pyramid.path import DottedNameResolver
import tornado.ioloop
import websocket_client

from mozsvc.config import load_into_settings


class WebSocket(websocket_client.WebSocket):

    def __init__(self, url):
        super(WebSocket, self).__init__(url)
        self.ponged = False

    def on_open(self):
        self.ping()

    def on_pong(self):
        self.ponged = True


def check_websocket_servers(storage, timeout):
    websockets = []
    for server in storage.get_edge_nodes():
        websockets.append((server, WebSocket('ws://' + server)))

    def callback():
        for server, ws in websockets:
            if not ws.ponged:
                storage.remove_edge_node(server)

    tornado.ioloop.IOLoop.instance().add_timeout(time.time() + timeout,
                                                 callback)


def main():
    parser = ArgumentParser('Monitor websocket servers.')
    parser.add_argument('config', help='path to the config file')
    args, settings = parser.parse_args(), {}
    load_into_settings(args.config, settings)
    config = settings['config']

    # Send a status report every 10 seconds.
    cfg = config.get_map('storage')
    storage = DottedNameResolver(None).resolve(cfg.pop('backend'))(**cfg)

    monitor = config.get_map('monitor')
    print 'Checking websocket servers every %s seconds.' % monitor['period']
    callback = partial(check_websocket_servers, storage, monitor['timeout'])
    tornado.ioloop.PeriodicCallback(callback, monitor['period'] * 1000).start()
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
