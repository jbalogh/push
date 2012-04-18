import os
import unittest2

import webtest

import push


class AppTest(unittest2.TestCase):
    # Tests for the full stack.

    def setUp(self):
        p = os.path
        ini = os.environ['PUSH_TEST_CONFIG']
        app = push.main({'__file__': p.abspath(ini)})
        self.testapp = webtest.TestApp(app)

    def test_token(self):
        self.testapp.get('/token/', status=405)

    def test_new_queue(self):
        self.testapp.post('/queue/', {'token': 't', 'domain': 'd'})
