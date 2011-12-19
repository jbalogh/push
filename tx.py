# Usage: twistd -ny tx.py
from twisted.application import internet
from twisted.application.service import Application
from twisted.internet.protocol import Factory, Protocol
from twisted.python import log

from txredisapi import SubscriberFactory, SubscriberProtocol
import txws


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
        self.factory.websockets.send(token, message.encode('utf-8'))


class PubSubFactory(SubscriberFactory):
    protocol = PubSub

    def __init__(self, websockets):
        self.websockets = websockets


application = Application('web sockets!')

wsfactory = WebSocketFactory()
service = internet.TCPServer(9999, txws.WebSocketFactory(wsfactory))
service.setServiceParent(application)

ff = PubSubFactory(wsfactory)
service = internet.TCPClient('127.0.0.1', 6379, ff)
service.setServiceParent(application)
