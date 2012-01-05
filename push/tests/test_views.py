import unittest2

import mock
from pyramid import testing
from nose.tools import eq_

from push import views
import push.storage.redis_


class ViewTest(unittest2.TestCase):

    def setUp(self):
        self.config = testing.setUp()

        self.request = testing.DummyRequest()

    def tearDown(self):
        testing.tearDown()

    def test_new_token(self):
        # POSTing gets a new token.
        storage_mock = mock.Mock()
        self.request.registry['storage'] = storage_mock
        storage_mock.new_token.return_value = mock.sentinel.token

        response = views.new_token(self.request)
        eq_(response, {'token': mock.sentinel.token})
