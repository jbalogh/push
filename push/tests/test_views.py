import json
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


def Request(post=None, matchdict=None):
    request = testing.DummyRequest(post=post)
    if matchdict:
        request.matchdict = matchdict
    if not hasattr(request, 'validated'):
        request.validated = {}
    return request


class ViewTest(unittest2.TestCase):

    def setUp(self):
        self.config = testing.setUp()

        self.request = Request()
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
        # Check the validator for various problems.
        request = Request(post={'token': ''})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: token', response)

        request = Request(post={'token': 'ok'})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: registration_id',
                     response)

        request = Request(post={'registration_id': 'ok'})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: token', response)

        request = Request(post={'token': 'ok', 'registration_id': ''})
        response = views.has_token_and_registration_id(request)
        assert_error(400, 'Missing required argument: registration_id',
                     response)

        request = Request(post={'token': 't', 'registration_id': 'r'})
        eq_(None, views.has_token_and_registration_id(request))

    def test_add_droid_id(self):
        # If we add a droid id we should be able to get it from storage.
        request = Request(post={'token': 't', 'registration_id': 'r'})
        eq_(views.add_droid_id(request), {'ok': 'ok'})

        eq_(self.storage.get_android_id('t'), 'r')

    def test_has_token_and_domain(self):
        # Check the validator for various problems.
        request = Request(post={'token': ''})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: token', response)

        request = Request(post={'token': 'ok'})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: domain', response)

        request = Request(post={'domain': 'ok'})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: token', response)

        request = Request(post={'token': 'ok', 'domain': ''})
        response = views.has_token_and_domain(request)
        assert_error(400, 'Missing required argument: domain', response)

        request = Request(post={'token': 't', 'domain': 'r'})
        eq_(None, views.has_token_and_domain(request))

    def test_new_queue(self):
        # A new queue should be available in storage and queuey.
        self.queuey.new_queue = lambda: 'new-queue'
        request = Request(post={'token': 't', 'domain': 'x.com'})
        request.route_url = lambda s, **kw: s.format(**kw)
        response = views.new_queue(request)
        eq_(response, {'queue': '/queue/new-queue/'})

        assert self.storage.user_owns_queue('t', 'new-queue')
        assert self.storage.domain_owns_queue('x.com', 'new-queue')
        eq_(self.storage.get_user_for_queue('new-queue'), 't')

    def test_queue_has_token(self):
        # Check the validator.
        request = Request(matchdict={'queue': 'queue'})
        assert_error(404, 'Not Found', views.queue_has_token(request))

        self.storage.new_queue('queue', 'user', 'domain')
        eq_(views.queue_has_token(request), None)
        eq_(request.validated['user'], 'user')

    @mock.patch('push.views.publish')
    @mock.patch('push.tests.mock_queuey.time')
    def test_new_message(self, time_mock, publish_mock):
        # New messages should be in queuey and pubsub.
        time_mock.time.return_value = 1
        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, 'user', 'domain')

        body = {'title': 'title', 'body': 'body'}
        request = Request(matchdict={'queue': queue}, post=body)
        request.validated['user'] = mock.sentinel.user

        response = views.new_message(request)
        # The body is in JSON since queuey just deals with strings.
        eq_(self.queuey.get_messages(queue)[0],
            {'body': json.dumps(body),
             'timestamp': 1,
             'key': response['key']})

        publish_mock.assert_called_with(mock.sentinel.user,
                                        {'queue': queue,
                                         'timestamp': 1,
                                         'body': body,
                                         'key': response['key']})
