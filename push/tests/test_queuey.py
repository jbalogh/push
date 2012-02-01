import json
import unittest2

import mock
from nose.tools import eq_

import push.queuey
import push.tests.mock_queuey


def Response(code, content):
    r = mock.Mock()
    r.status_code = code
    r.content = content
    return r


class TestQueuey(unittest2.TestCase):

    def setUp(self):
        # Get a real queuey to poke at.
        self.queuey = push.queuey.Queuey('/url/', 'app-key')
        # Get a mock queuey to generate fake responses.
        self.mock_queuey = push.tests.mock_queuey.MockQueuey()

    def response(self, code, content):
        response = Response(code, content)
        self.queuey.json_response(response)
        return response

    @mock.patch('push.queuey.requests')
    def test_request(self, requests_mock):
        self.queuey.request()
        requests_mock.session.assert_called_with(
            headers={'X-Application-Key': 'app-key'},
            hooks={'response': self.queuey.json_response})

    def test_json_response(self):
        response = Response(200, '{}')
        self.queuey.json_response(response)
        eq_(response.json, {})

        with self.assertRaises(push.queuey.QueueyException):
            response = Response(400, '')
            self.queuey.json_response(response)

        with self.assertRaises(push.queuey.QueueyException):
            response = Response(200, 'abab')
            self.queuey.json_response(response)

    def test_new_queue(self):
        self.queuey.request = mock.Mock()
        post_mock = self.queuey.request.return_value.post

        queue = self.mock_queuey.new_queue()
        response = self.response(200, json.dumps({'queue_name': queue}))
        post_mock.return_value = response

        eq_(self.queuey.new_queue(), queue)
        post_mock.assert_called_with('/url/queue/')

    def test_new_message(self):
        self.queuey.request = mock.Mock()
        post_mock = self.queuey.request.return_value.post

        queue = self.mock_queuey.new_queue()
        message = self.mock_queuey.new_message(queue, 'ok')
        response = self.response(200, json.dumps(message))
        post_mock.return_value = response

        eq_(self.queuey.new_message(queue, 'ok'), message)
        post_mock.assert_called_with('/url/queue/%s/' % queue, 'ok')

    def test_get_messages(self):
        self.queuey.request = mock.Mock()
        get_mock = self.queuey.request.return_value.get

        queue = self.mock_queuey.new_queue()
        queue_url = '/url/queue/%s/' % queue

        response = self.response(200, json.dumps({'messages': []}))
        get_mock.return_value = response

        eq_(self.queuey.get_messages(queue), [])
        get_mock.assert_called_with(queue_url, params={})

        self.queuey.get_messages(queue, since=1)
        get_mock.assert_called_with(queue_url, params={'since_timestamp': 1})


        self.queuey.get_messages(queue, limit=2, order='asc')
        get_mock.assert_called_with(queue_url,
                                    params={'limit': 2, 'order': 'asc'})
