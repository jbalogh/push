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


def Request(params=None, post=None, matchdict=None, headers=None):
    request = testing.DummyRequest(params=params, post=post, headers=headers)
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
             'key': response['messages'][0]['key']})

        publish_mock.assert_called_with(request, mock.sentinel.user,
                                        {'queue': queue,
                                         'timestamp': 1,
                                         'body': body,
                                         'key': response['messages'][0]['key']})

    def test_valid_float(self):
        # Check the validator.
        request = Request()
        assert_error(400, 'Need a `timestamp` parameter.',
                     views.valid_float(request))

        request = Request(post={'timestamp': 'aab'})
        assert_error(400, '`timestamp` must be a float.',
                     views.valid_float(request))

        # Make sure a good value goes in request.validated.
        request = Request(post={'timestamp': '1.2'})
        eq_(views.valid_float(request), None)
        eq_(request.validated['timestamp'], 1.2)

    def test_add_timestamp(self):
        # Check that PUTing a timestamp adds it to storage.
        request = Request(post={'timestamp': 1.2},
                          matchdict={'queue': 'queue'})
        views.valid_float(request)
        eq_(views.add_timestamp(request), {})

        eq_(self.storage.get_queue_timestamp('queue'), 1.2)

    def test_check_token(self):
        # Check the validator.
        request = Request()
        assert_error(400, 'An X-Auth-Token header must be included.',
                     views.check_token(request))

        request = Request(headers={'x-auth-token': 'token'},
                          matchdict={'queue': 'queue'})
        assert_error(404, 'Not Found.', views.check_token(request))

        self.storage.new_queue('queue', 'user', 'domain')
        request = Request(headers={'x-auth-token': 'user'},
                          matchdict={'queue': 'queue'})
        eq_(views.check_token(request), None)

    @mock.patch('push.tests.mock_queuey.time')
    def test_get_messages(self, time_mock):
        # Check that we can get both of the messages back.
        time_mock.time = [3, 2, 1].pop

        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, 'user', 'domain')

        key1 = self.queuey.new_message(queue, 'one')['messages'][0]['key']
        key2 = self.queuey.new_message(queue, 'two')['messages'][0]['key']

        request = Request(headers={'x-auth-token': 'user'},
                          matchdict={'queue': queue})
        eq_(views.get_messages(request), {
            'messages': [{'body': 'one', 'timestamp': 1, 'key': key1},
                         {'body': 'two', 'timestamp': 2, 'key': key2}],
            'last_seen': 0})

    def test_get_messages_last_seen(self):
        # Check that the last_seen parameter is sent properly.
        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, 'user', 'domain')

        request = Request(headers={'x-auth-token': 'user'},
                          matchdict={'queue': queue})
        eq_(views.get_messages(request), {'messages': [], 'last_seen': 0})

        self.storage.set_queue_timestamp(queue, 12)
        eq_(views.get_messages(request), {'messages': [], 'last_seen': 12})

    @mock.patch('push.tests.mock_queuey.time')
    def test_get_messages_since(self, time_mock):
        # Check that we honor the since parameter.
        time_mock.time = [3, 2, 1].pop

        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, 'user', 'domain')

        key1 = self.queuey.new_message(queue, 'one')['messages'][0]['key']
        key2 = self.queuey.new_message(queue, 'two')['messages'][0]['key']

        request = Request(params={'since': 1},
                          headers={'x-auth-token': 'user'},
                          matchdict={'queue': queue})
        eq_(views.get_messages(request), {
            'messages': [{'body': 'two', 'timestamp': 2, 'key': key2}],
            'last_seen': 0})
