"""
Drive through notifications client interactions.
"""
import json
import sys
import textwrap
import threading
import time

import requests
import websocket_client
from tornado import ioloop


def print_request(request):
    lines = ['%s %s' % (request.method, request.url)]
    lines.extend(sorted(': '.join(item) for item in request.headers.items()))
    if request.data:
        lines.extend(['', '',
                      '&'.join(sorted('='.join(x) for x in request.data))])
    print '::', '\n:: '.join(lines), '\n'


def print_response(response):
    lines = ['HTTP/1.1 %s' % response.status_code]
    lines.extend(sorted(': '.join(item) for item in response.headers.items()))
    if response.content:
        lines.extend(['', '', response.content])
    print '::', '\n:: '.join(lines), '\n'


def wait(seconds, test, sleep=1):
    count = 0
    while not test() and count < seconds:
        time.sleep(sleep)
        count += 1


class WebSocket(websocket_client.WebSocket):

    def __init__(self, url, token):
        super(WebSocket, self).__init__(url)
        self.token = token
        self.messages = []
        self.is_open = False

    def on_open(self):
        self.is_open = True
        self.write_message('token: ' + self.token)

    def write_message(self, data):
        print '>>', data, '\n'
        super(WebSocket, self).write_message(data)

    def on_message(self, data):
        print '>>', data, '\n'
        self.messages.append(data)


def step(desc):
    # Indent the text in a numbered paragraph.
    if desc[0].isdigit():
        joiner = '\n' + ' ' * (1 + desc.index(' '))
    else:
        joiner = '\n'
    print '\n\n', joiner.join(textwrap.wrap(desc, 72)), '\n', '=' * 40


def main(api_url):
    # This is our local store of push URLs keyed by domain.
    queues = {}

    http = requests.session(hooks={'pre_request': print_request,
                                   'response': print_response})

    step('1. Get a token. This is how we identify ourselves to the service.')
    r = http.post(api_url + '/token/')
    assert r.status_code == 200
    token = json.loads(r.content)['token']
    print 'Token:', token, '\n'

    # 2. Sync push URLs. If we were a browser, we'd want our push URLs to be up
    #    to date with the user's other clients.
    # 3. Get stored messages.
    step('4. Get a list of socket servers')
    r = http.get(api_url + '/nodes/')
    assert r.status_code == 200
    nodes = json.loads(r.content)['nodes']
    print 'WebSocket nodes:', nodes

    step('5. Try connecting to a socket server.')
    print 'We identify ourselves on the websocket by sending the token.\n'
    ws = WebSocket('ws://' + nodes[0], token)
    wait(10, lambda: ws.is_open)
    print 'Connected.'

    step('6. Get a new push URL. If we were in a browser, we\'d be doing this '
         'on behalf of a web site.')
    domain = 'example.com'
    r = http.post(api_url + '/queue/', {'token': token, 'domain': domain})
    assert r.status_code == 200
    queues[domain] = json.loads(r.content)['queue']

    print 'This is where the client would return the push URL to the website.'

    step('7. Listen for messages coming from the socket server.')
    print 'Sending a fake message.'
    r = http.post(queues[domain], {'title': 'fake message', 'body': 'ok'})
    assert r.status_code == 200

    # Wait for convergence.
    if not ws.messages:
        print 'Waiting on the websocket...\n'
        wait(10, lambda: ws.messages)

    assert len(ws.messages) == 1
    print 'Got the message on the websocket.'

    # 8. Revoke push URLs after user action.
    # 9. Tell the server to mark messages as read after user action.
    # 10. Mark messages as read when the server notifies us.


if __name__ == '__main__':
    # Start the tornado IO loop in another thread.
    io_thread = threading.Thread(target=ioloop.IOLoop.instance().start)
    io_thread.start()

    try:
        main(*sys.argv[1:])
    finally:
        # Kill the IO loop.
        ioloop.IOLoop.instance().stop()
        io_thread.join()
