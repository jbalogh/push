import unittest2

import mock
from pyramid import testing
from nose.tools import eq_

from push import views
import push.storage.mem

from mock_queuey import MockQueuey


def assert_error(code, message, response):
    eq_(code, response[0])
    eq_(message, response[1])


class ViewTest(unittest2.TestCase):

    def setUp(self):
        self.config = testing.setUp()

        self.request = testing.DummyRequest()
        self.storage = push.storage.mem.Storage()
        self.queuey = MockQueuey()
        self.request.registry['storage'] = self.storage
        self.request.registry['queuey'] = self.queuey

    def tearDown(self):
        testing.tearDown()

    def test_new_token(self):
        # POSTing gets a new token.
        storage_mock = mock.Mock()
        self.request.registry['storage'] = storage_mock
        storage_mock.new_token.return_value = mock.sentinel.token

        response = views.new_token(self.request)
        eq_(response, {'token': mock.sentinel.token})

    def test_has_token_and_registration_id(self):
        request = testing.DummyRequest(post={'token': ''})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: token', response)

        request = testing.DummyRequest(post={'token': 'ok'})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: registration_id',
                     response)

        request = testing.DummyRequest(post={'registration_id': 'ok'})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: token', response)

        request = testing.DummyRequest(post={'token': 'ok',
                                             'registration_id': ''})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: registration_id',
                     response)

        request = testing.DummyRequest(post={'token': 't',
                                             'registration_id': 'r'})
        eq_(None, views.has_token_and_registration_id(request))

    def test_add_droid_id(self):
        request = testing.DummyRequest(post={'token': 't',
                                             'registration_id': 'r'})
        eq_(views.add_droid_id(request), {'ok': 'ok'})

        eq_(self.storage.get_android_id('t'), 'r')

    def test_has_token_and_domain(self):
        request = testing.DummyRequest(post={'token': ''})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: token', response)

        request = testing.DummyRequest(post={'token': 'ok'})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: domain', response)

        request = testing.DummyRequest(post={'domain': 'ok'})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: token', response)

        request = testing.DummyRequest(post={'token': 'ok',
                                             'domain': ''})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: domain', response)

        request = testing.DummyRequest(post={'token': 't',
                                             'domain': 'r'})
        eq_(None, views.has_token_and_domain(request))

    def test_new_queue(self):
        self.queuey.new_queue = lambda: 'new-queue'
        request = testing.DummyRequest(post={'token': 't', 'domain': 'x.com'})
        request.route_url = lambda s, **kw: s.format(**kw)
        response = views.new_queue(request)
        eq_(response, {'queue': '/queue/new-queue/'})

        assert self.storage.user_owns_queue('t', 'new-queue')
        assert self.storage.domain_owns_queue('x.com', 'new-queue')
        eq_(self.storage.get_user_for_queue('new-queue'), 't')
