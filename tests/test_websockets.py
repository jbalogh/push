import os
import unittest2

import mock
import websockets
from nose.tools import eq_

CONFIG_PATH = os.environ['PUSH_TEST_CONFIG']


class WebsocketTest(unittest2.TestCase):

    def setUp(self):
        app_mock = mock.Mock()
        app_mock.ui_methods.iteritems.return_value = []
        app_mock.ui_modules.iteritems.return_value = []
        self.socket_handler = websockets.SocketHandler(app_mock, app_mock)
        self.pusher = websockets.Push(mock.Mock())
        websockets.CONNECTIONS = 0
        websockets.SOCKETS = {}

    def test_websocket_on_open(self):
        # Opening a sockets bumps the connection.
        self.socket_handler.open()
        eq_(websockets.CONNECTIONS, 1)

    def test_websocket_on_message(self):
        # Sending a message does nothing.
        self.socket_handler.on_message('hi')
        eq_(websockets.SOCKETS, {})

        # Sending a message prefixed with token: puts that token in sockets.
        self.socket_handler.on_message('token: t')
        eq_(websockets.SOCKETS, {'t': self.socket_handler})
        eq_(self.socket_handler.token, 't')

    def test_websocket_on_close(self):
        # No token set up. Nothing happens.
        self.socket_handler.on_close()
        eq_(websockets.SOCKETS, {})

        # The token isn't in SOCKETS. Nothing happens.
        self.socket_handler.token = 't'
        self.socket_handler.on_close()
        eq_(websockets.SOCKETS, {})

        # The token goes in SOCKETS after the message, and gets removed
        # afterwards.
        self.socket_handler.open()
        self.socket_handler.on_message('token: t')
        eq_(websockets.SOCKETS, {'t': self.socket_handler})
        eq_(websockets.CONNECTIONS, 1)
        self.socket_handler.on_close()
        eq_(websockets.SOCKETS, {})
        eq_(websockets.CONNECTIONS, 0)

    def test_zmq_recv(self):
        # The first piece of the message (the SUBSCRIBE flag) gets dropped.
        with mock.patch.object(self.pusher, 'send') as send_mock:
            msg = 'a', 'b', 'c'
            self.pusher.recv(msg)
            send_mock.assert_called_with('b', 'c')

    def test_zmq_send_no_token(self):
        socket = websockets.SOCKETS['token'] = mock.Mock()
        msg = ('PUSH', 't', 'hi')
        self.pusher.recv(msg)
        eq_(socket.call_count, 0)

    def test_zmq_send_with_token(self):
        socket = websockets.SOCKETS['token'] = mock.Mock()
        msg = ('PUSH', 'token', 'hi')
        self.pusher.recv(msg)
        socket.write_message.assert_called_with('hi')

    def test_zmq_send_bad_socket(self):
        websockets.CONNECTIONS = 2
        socket = websockets.SOCKETS['token'] = mock.Mock()
        socket.write_message.side_effect = AttributeError

        msg = ('PUSH', 'token', 'hi')
        self.pusher.recv(msg)
        # The bad socket was removed from the lookup table.
        eq_(websockets.SOCKETS, {})
        eq_(websockets.CONNECTIONS, 1)

    def test_report_status(self):
        websockets.CONNECTIONS = mock.sentinel.CONNECTIONS
        storage = mock.Mock()
        websockets.report_status(storage, '127.0.0.1')
        storage.add_edge_node.assert_called_with('127.0.0.1',
                                                 mock.sentinel.CONNECTIONS)
