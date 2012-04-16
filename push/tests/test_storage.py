import hashlib
import unittest2

import mock
from nose.tools import eq_

import push.storage.mem
import push.storage.redis_


class StorageTest(unittest2.TestCase):
    __test__ = False

    @mock.patch('push.storage.base.os')
    def test_new_token(self, os_mock):
        os_mock.urandom.return_value = 'ok'
        eq_(self.storage.new_token(64), hashlib.sha1('ok').hexdigest())
        os_mock.urandom.assert_called_with(64)

    def test_get_queues(self):
        self.storage.new_queue('queue', 'user', 'domain')
        eq_(self.storage.get_queues('user'), {'domain': 'queue'})

    def test_user_owns_queue(self):
        assert not self.storage.user_owns_queue('user', 'queue')
        self.storage.new_queue('queue', 'user', 'domain')
        assert self.storage.user_owns_queue('user', 'queue')

    def test_domain_owns_queue(self):
        assert not self.storage.domain_owns_queue('domain', 'queue')
        self.storage.new_queue('queue', 'user', 'domain')
        assert self.storage.domain_owns_queue('domain', 'queue')

    def test_get_user_for_queue(self):
        eq_(self.storage.get_user_for_queue('queue'), None)
        self.storage.new_queue('queue', 'user', 'domain')
        eq_(self.storage.get_user_for_queue('queue'), 'user')

    def test_add_edge_node(self):
        self.storage.add_edge_node('a', 4)
        self.storage.add_edge_node('b', 5)
        self.storage.add_edge_node('c', 6)
        eq_(self.storage.get_edge_nodes(1), ['a'])
        eq_(self.storage.get_edge_nodes(2), ['a', 'b'])

    def test_get_edge_nodes_all(self):
        self.storage.add_edge_node('a', 4)
        self.storage.add_edge_node('b', 5)
        self.storage.add_edge_node('c', 6)
        eq_(self.storage.get_edge_nodes(), ['a', 'b', 'c'])

    def test_remove_edge_node(self):
        self.storage.add_edge_node('a', 4)
        self.storage.add_edge_node('b', 5)
        self.storage.add_edge_node('c', 6)
        self.storage.remove_edge_node('a')
        eq_(self.storage.get_edge_nodes(), ['b', 'c'])


class MemStorageTest(StorageTest):
    __test__ = True

    def setUp(self):
        self.storage = push.storage.mem.Storage()


class RedisStorageTest(StorageTest):
    __test__ = True

    def setUp(self):
        self.storage = push.storage.redis_.Storage(db=9)
        self.storage.redis.flushdb()
