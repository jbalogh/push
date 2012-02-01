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

    def test_android_id(self):
        self.storage.set_android_id('user', 'droid')
        eq_(self.storage.get_android_id('user'), 'droid')

    def test_set_queue_timestamp(self):
        self.storage.set_queue_timestamp('queue', 12)
        eq_(self.storage.get_queue_timestamp('queue'), 12)

    def test_set_queue_timestamp_greater(self):
        # New values must be greater than the old value.
        self.storage.set_queue_timestamp('queue', 12)
        self.storage.set_queue_timestamp('queue', 2)
        eq_(self.storage.get_queue_timestamp('queue'), 12)

    def test_get_queue_timestamp(self):
        eq_(self.storage.get_queue_timestamp('unknown'), 0)

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


class MemStorageTest(StorageTest):
    __test__ = True

    def setUp(self):
        self.storage = push.storage.mem.Storage()


class RedisStorageTest(StorageTest):
    __test__ = True

    def setUp(self):
        self.storage = push.storage.redis_.Storage(db=9)
        self.storage.redis.flushdb()
