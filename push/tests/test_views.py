import json
import os
import unittest2

import mock
import zmq
from pyramid import testing
from nose.tools import eq_

from mozsvc.config import load_into_settings

from push import views
import push.storage.mem

from mock_queuey import MockQueuey


def Request(params=None, post=None, matchdict=None, headers=None, **kw):

    class Errors(list):

        def add(self, where, key, msg):
            self.append((where, key, msg))

    testing.DummyRequest.json_body = property(lambda s: json.loads(s.body))

    request = testing.DummyRequest(params=params, post=post,
                                   headers=headers, **kw)
    request.route_url = lambda s, **kw: s.format(**kw)
    if matchdict:
        request.matchdict = matchdict
    if not hasattr(request, 'validated'):
        request.validated = {}
    if not hasattr(request, 'errors'):
        request.errors = Errors()
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
        storage_mock.new_token.return_value = 'TOKEN'

        response = views.new_token(self.request)
        eq_(response, {'token': 'TOKEN', 'queue': '/queue/TOKEN/'})

    def test_has_token_and_domain(self):
        # Check the validator for various problems.
        request = Request(post={'token': ''})
        views.has_token_and_domain(request)
        eq_(len(request.errors), 2)
        eq_(request.errors[0][:2], ('body', 'token'))
        eq_(request.errors[1][:2], ('body', 'domain'))

        request = Request(post={'token': 'ok'})
        views.has_token_and_domain(request)
        eq_(len(request.errors), 1)
        eq_(request.errors[0][:2], ('body', 'domain'))

        request = Request(post={'domain': 'ok'})
        views.has_token_and_domain(request)
        eq_(len(request.errors), 1)
        eq_(request.errors[0][:2], ('body', 'token'))

        request = Request(post={'token': 'ok', 'domain': ''})
        views.has_token_and_domain(request)
        eq_(len(request.errors), 1)
        eq_(request.errors[0][:2], ('body', 'domain'))

        request = Request(post={'token': 't', 'domain': 'r'})
        views.has_token_and_domain(request)
        eq_(len(request.errors), 0)

    def test_new_queue(self):
        # A new queue should be available in storage.
        self.storage.new_token = lambda: 'new-queue'
        request = Request(post={'token': 't', 'domain': 'x.com'})
        response = views.new_queue(request)
        eq_(response, {'queue': '/queue/new-queue/'})

        assert self.storage.user_owns_queue('t', 'new-queue')
        eq_(self.storage.get_user_for_queue('new-queue'), 't')

    def test_delete_queue(self):
        request = Request(post={'token': 't', 'domain': 'x.com'})
        queue = filter(None, views.new_queue(request)['queue'].split('/'))[-1]

        request = Request(params={'token': 't'}, matchdict={'queue': queue})
        views.delete_queue(request)
        eq_(views.get_queues(Request(params={'token': 't'})), {})

    def test_delete_queue_404(self):
        request = Request(post={'token': 't', 'domain': 'x.com'})
        queue = filter(None, views.new_queue(request)['queue'].split('/'))[-1]

        # A valid token with an invalid queue gets a 404.
        request = Request(params={'token': 't'}, matchdict={'queue': 'x'})
        eq_(views.delete_queue(request).code, 404)

        # An invalid token with a valid queue gets a 404.
        request = Request(params={'token': 'x'}, matchdict={'queue': queue})
        eq_(views.delete_queue(request).code, 404)

    def test_has_token(self):
        request = Request(params={'token': 't'})
        eq_(None, views.has_token(request))

        request = Request()
        views.has_token(request)
        eq_(len(request.errors), 1)
        eq_(request.errors[0][:2], ('body', 'token'))

    def test_get_queues(self):
        token = views.new_token(Request())['token']
        request = Request(post={'token': token, 'domain': 'domain'})
        queue = views.new_queue(request)['queue']

        request = Request(params={'token': token})
        response = views.get_queues(request)
        eq_(response, {'domain': queue})

    @mock.patch('push.views.publish')
    @mock.patch('push.tests.mock_queuey.time')
    def test_new_message(self, time_mock, publish_mock):
        # New messages should be in queuey and pubsub.
        token = views.new_token(Request(post={}))['token']
        time_mock.time.return_value = 1
        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, token, 'domain')

        body = {'title': 'title', 'body': 'body'}
        request = Request(matchdict={'queue': queue}, post=body)
        views.message_validator(request)
        response = views.new_message(request)

        # The body is in JSON since queuey just deals with strings.
        self.assertDictEqual(
            self.queuey.get_messages(token)[0],
            {u'body': json.dumps({'queue': queue, 'body': body}),
             u'timestamp': '1',
             u'partition': 1,
             u'message_id': response['messages'][0]['key']})

        publish_mock.assert_called_with(
            request, token, {'queue': queue,
                             'timestamp': '1',
                             'body': body,
                             'key': response['messages'][0]['key']})

    @mock.patch('push.views.publish')
    def test_new_message_json(self, publish_mock):
        # A new message coming through as JSON works fine.
        token = views.new_token(Request(post={}))['token']
        queue = self.storage.new_token()
        self.storage.new_queue(queue, token, 'domain')

        body = {'title': 'title', 'body': 'body'}
        request = Request(matchdict={'queue': queue},
                          body=json.dumps(body))

        views.message_validator(request)
        response = views.new_message(request)
        message = response['messages'][0]
        publish_mock.assert_called_with(
            request, token, {'queue': queue,
                             'timestamp': message['timestamp'],
                             'body': body,
                             'key': message['key']})

    def test_message_validator_urlencoded(self):
        # Messages can be form-urlencoded.
        request = Request(post={'title': 'hi'})
        views.message_validator(request)
        eq_(request.validated['message'], {'title': 'hi'})
        eq_(request.errors, [])

    def test_message_validator_json(self):
        # Messages can be JSON.
        request = Request(body=json.dumps({'title': 'hi'}))
        views.message_validator(request)
        eq_(request.validated['message'], {'title': 'hi'})
        eq_(request.errors, [])

    def test_message_validator_no_body(self):
        # A message with no body is invalid.
        request = Request(post={})
        views.message_validator(request)
        assert 'message' not in request.validated
        eq_(len(request.errors), 1)
        eq_(request.errors[0][:-1], ('body', 'body'))

    def test_message_validator_action_read(self):
        # No validation happens if action=read.
        request = Request(post={'action': 'read', 'key': 'k'})
        views.message_validator(request)
        assert 'message' not in request.validated
        eq_(request.errors, [])

    def test_message_validator_invalid_key(self):
        # Only valid keys are passed to the view.
        valid = {'title': 'title',
                 'body': 'body',
                 'actionUrl': 'actionUrl',
                 'replaceId': 'replaceId'}

        # All our valid keys make it through.
        request = Request(post=valid)
        views.message_validator(request)
        eq_(request.validated['message'], valid)
        eq_(request.errors, [])

        # Invalid keys are silently discarded.
        invalid = dict(valid)
        invalid['bad'] = 'bad'
        request = Request(post=invalid)
        views.message_validator(request)
        eq_(request.validated['message'], valid)
        eq_(request.errors, [])

    def test_new_message_404(self):
        # POSTing to a queue without an associated token returns a 404.
        request = Request(post={}, matchdict={'queue': 'queue'})
        eq_(views.new_message(request).code, 404)

    @mock.patch('push.views.publish')
    def test_mark_message_read(self, publish_mock):
        # Check that we can mark a message as read.
        token = views.new_token(Request(post={}))['token']
        request = Request(post={'action': 'read', 'key': 'key'},
                          matchdict={'queue': token})
        eq_(views.new_message(request)['status'], 'ok')

    def test_mark_message_read_no_key(self):
        request = Request(post={'action': 'read'})
        eq_(views.new_message(request).code, 404)

    @mock.patch('push.views.publish')
    def test_get_message_read(self, publish_mock):
        # Check the format of the read message marker.
        token = views.new_token(Request(post={}))['token']
        request = Request(post={'action': 'read', 'key': 'key'},
                          matchdict={'queue': token})
        response = views.new_message(request)['messages'][0]

        req = Request(matchdict={'queue': token})
        self.assertListEqual(views.get_messages(req)['messages'],
                             [{'body': {'read': 'key'},
                               'queue': token,
                               'key': response['key'],
                               'timestamp': str(response['timestamp'])}])

        # The format should match the pubsub'd message.
        expected = views.get_messages(req)['messages'][0]
        publish_mock.assert_called_with(request, token, expected)

    @mock.patch('push.tests.mock_queuey.time')
    def test_get_messages(self, time_mock):
        # Check that we can get both of the messages back.
        time_mock.time = [3, 2, 1].pop

        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, 'user', 'domain')

        msg = json.dumps({'queue': queue, 'body': {}})
        key1 = self.queuey.new_message(queue, msg)['messages'][0]['key']
        key2 = self.queuey.new_message(queue, msg)['messages'][0]['key']

        request = Request(params={'token': 'user'},
                          matchdict={'queue': queue})
        eq_(views.get_messages(request), {
            'messages': [{'body': {},
                          'timestamp': '1',
                          'queue': queue,
                          'key': key1},
                         {'body': {},
                          'queue': queue,
                          'timestamp': '2',
                          'key': key2}]})

    def test_get_messages_404(self):
        # Asking for a queue without a matching token returns a 404.
        request = Request(params={'token': 'ok'}, matchdict={'queue': 'queue'})
        eq_(views.get_messages(request).code, 404)

    @mock.patch('push.tests.mock_queuey.time')
    def test_get_messages_since(self, time_mock):
        # Check that we honor the since parameter.
        time_mock.time = [3, 2, 1].pop

        queue = self.queuey.new_queue()
        self.storage.new_queue(queue, 'user', 'domain')

        msg = json.dumps({'queue': queue, 'body': {}})
        key1 = self.queuey.new_message(queue, msg)['messages'][0]['key']
        key2 = self.queuey.new_message(queue, msg)['messages'][0]['key']

        request = Request(params={'since': 1, 'token': 'user'},
                          matchdict={'queue': queue})
        eq_(views.get_messages(request), {
            'messages': [{'body': {},
                          'timestamp': '2',
                          'queue': queue,
                          'key': key2}]})

    def test_get_nodes(self):
        self.storage.add_edge_node('a', 8)
        self.storage.add_edge_node('b', 6)
        self.storage.add_edge_node('c', 7)
        eq_(views.get_nodes(Request()), {'nodes': ['b', 'c', 'a']})


class PublishTest(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        settings = {}
        load_into_settings(os.environ['PUSH_TEST_CONFIG'], settings)
        cls.config = settings['config']

        cls.pull_socket = zmq.Context().socket(zmq.PULL)
        cls.pull_socket.setsockopt(zmq.LINGER, 0)
        cls.pull_socket.bind(cls.config.get('zeromq', 'pull'))

    @classmethod
    def tearDownClass(cls):
        cls.pull_socket.close()

    def test_publish(self):
        request = mock.Mock()
        cfg = self.config.get('zeromq', 'push')
        request.registry.settings = {'zeromq.push': cfg}

        views.publish(request, 'token', 'message')

        msg = self.pull_socket.recv_multipart()
        self.assertEqual(tuple(msg), ('PUSH', 'token', json.dumps('message')))
