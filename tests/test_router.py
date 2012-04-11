import os
import time
import unittest2

import circus
import zmq

from mozsvc.config import load_into_settings


CONFIG_PATH = os.environ['PUSH_TEST_CONFIG']


class RouterTest(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        settings = {}
        load_into_settings(CONFIG_PATH, settings)
        cls.config = settings['config']

        cls.arbiter = circus.get_arbiter([
            {'cmd': 'python router.py %s' % CONFIG_PATH,
             'shell': True}
        ], background=True)
        cls.arbiter.start()
        # I hope the router is set up once we're done sleeping!
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.arbiter.stop()

    def test_router(self):
        context = zmq.Context()
        push_socket = context.socket(zmq.PUSH)
        push_socket.setsockopt(zmq.LINGER, 0)
        push_socket.connect(self.config.get('zeromq', 'push'))

        sub_socket = context.socket(zmq.SUB)
        sub_socket.setsockopt(zmq.LINGER, 0)
        sub_socket.connect(self.config.get('zeromq', 'sub'))
        sub_socket.setsockopt(zmq.SUBSCRIBE, 'TEST')

        message = ('TEST', 'testo')
        push_socket.send_multipart(message, zmq.NOBLOCK)
        msg = sub_socket.recv_multipart()
        self.assertEqual(tuple(msg), message)
