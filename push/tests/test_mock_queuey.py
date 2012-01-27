import unittest2

import mock
from nose.tools import eq_

from mock_queuey import MockQueuey


class TestMockQueuey(unittest2.TestCase):

    def setUp(self):
        self.mq = MockQueuey()

        patcher = mock.patch('push.tests.mock_queuey.time')
        self.time_mock = patcher.start()
        self.time_mock.time = [3, 2, 1].pop
        self.addCleanup(patcher.stop)

        patcher = mock.patch('push.tests.mock_queuey.uuid')
        self.uuid_mock = patcher.start()
        self.uuid_mock.uuid4.return_value.hex = 'uuid'
        self.addCleanup(patcher.stop)

    def test_new_queue(self):
        eq_(self.mq.new_queue(), 'uuid')
        eq_(self.mq.new_queue(), 'uuid')

    def test_new_message(self):
        queue = self.mq.new_queue()
        eq_(self.mq.new_message(queue, 'one'),
            {'key': 'uuid',
             'partition': 1,
             'status': 'ok',
             'timestamp': 1})

    def test_get_messages(self):
        queue = self.mq.new_queue()
        self.mq.new_message(queue, 'one')
        self.mq.new_message(queue, 'two')
        eq_(self.mq.get_messages(queue), [
            {'body': 'two',
             'key': 'uuid',
             'timestamp': 2},
            {'body': 'one',
             'key': 'uuid',
             'timestamp': 1},
        ])

    def test_get_messages_limit(self):
        queue = self.mq.new_queue()
        self.mq.new_message(queue, 'one')
        self.mq.new_message(queue, 'two')
        eq_(self.mq.get_messages(queue, limit=1), [
            {'body': 'two',
             'key': 'uuid',
             'timestamp': 2},
        ])

    def test_get_messages_since(self):
        queue = self.mq.new_queue()
        self.mq.new_message(queue, 'one')
        self.mq.new_message(queue, 'two')
        eq_(self.mq.get_messages(queue, since=1), [
            {'body': 'two',
             'key': 'uuid',
             'timestamp': 2},
        ])
    def test_get_messages_order(self):
        queue = self.mq.new_queue()
        self.mq.new_message(queue, 'one')
        self.mq.new_message(queue, 'two')
        eq_(self.mq.get_messages(queue, order='ascending'), [
            {'body': 'one',
             'key': 'uuid',
             'timestamp': 1},
            {'body': 'two',
             'key': 'uuid',
             'timestamp': 2},
        ])
