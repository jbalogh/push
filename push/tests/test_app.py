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
        self.testapp.post('/token/', status=200)
