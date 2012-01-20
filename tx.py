# Usage: twistd -ny tx.py
import json

from twisted.application import internet
from twisted.application.service import Application
from twisted.internet.protocol import Factory, Protocol
from twisted.python import log

from txredisapi import SubscriberFactory, SubscriberProtocol
import txws

import c2dm
from push.storage.redis_ import Storage


class WebSocket(Protocol):

    def __init__(self):
        self.token = None

    def connectionLost(self, reason):
        if self.token in self.factory.clients:
            del self.factory.clients[self.token]

    def dataReceived(self, data):
        self.token = data.strip()
        self.factory.clients[self.token] = self


class WebSocketFactory(Factory):
    protocol = WebSocket

    def __init__(self):
        self.clients = {}

    def send(self, token, message):
        if token in self.clients:
            self.clients[token].transport.write(message)


class PubSub(SubscriberProtocol):

    def connectionMade(self):
        self.psubscribe('push.*')

    def messageReceived(self, pattern, channel, message):
        token = channel[len('push.'):]
        message = message.encode('utf-8')
        self.factory.websockets.send(token, message)
        self.send_to_droid(token, message)

    def send_to_droid(self, token, message):
        droid_id = self.factory.storage.get_android_id(token)
        if droid_id:
            print 'droid message', message
            message = json.loads(message)
            c2dm.c2dm(droid_id, 'ok', json.loads(message['body']))


class PubSubFactory(SubscriberFactory):
    protocol = PubSub

    def __init__(self, websockets):
        self.websockets = websockets
        self.storage = Storage(host='localhost', port=6379)


application = Application('push')

wsfactory = WebSocketFactory()
service = internet.TCPServer(9999, txws.WebSocketFactory(wsfactory))
service.setServiceParent(application)

ff = PubSubFactory(wsfactory)
service = internet.TCPClient('127.0.0.1', 6379, ff)
service.setServiceParent(application)
