# Usage: twistd -ny tx.py
from twisted.application import internet
from twisted.application.service import Application
from twisted.internet.protocol import Factory, Protocol
from twisted.python import log

from txredisapi import SubscriberFactory, SubscriberProtocol
import txws


sockets = []


class WebSocket(Protocol):

    def connectionMade(self):
        self.factory.clients.add(self)

    def connectionLost(self, reason):
        self.factory.clients.remove(self)

    def dataReceived(self, data):
        log.msg('data:', data)
        self.transport.write(data)


class WebSocketFactory(Factory):
    protocol = WebSocket

    def __init__(self):
        self.clients = set()

    def broadcast(self, msg):
        for client in self.clients:
            client.transport.write(msg)


class PubSub(SubscriberProtocol):

    def connectionMade(self):
        self.subscribe('push')

    def messageReceived(self, pattern, channel, message):
        self.factory.websockets.broadcast(message.encode('utf-8'))


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
