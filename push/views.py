import json

import zmq

from cornice.service import Service

# Process-level singleton zmq pusher socket.
PUSH_SOCKET = None

tokens = Service(name='tokens', path='/token/')
queues = Service(name='queues', path='/queue/')
messages = Service(name='messages', path='/queue/{queue}/')
nodes = Service(name='nodes', path='/nodes/')


@tokens.post()
def new_token(request):
    """Get a new random, opaque string."""
    storage = request.registry['storage']
    return {'token': storage.new_token()}


def has_token_and_domain(request):
    """Non-empty token and domain values must be give in the POST body."""
    for key in ('token', 'domain'):
        if not request.POST.get(key):
            return 400, 'Missing required argument: ' + key


@queues.post(validators=has_token_and_domain)
def new_queue(request):
    """Create a new queue between the given user and domain."""
    queuey = request.registry['queuey']
    storage = request.registry['storage']

    queue = queuey.new_queue()
    token, domain = request.POST['token'], request.POST['domain']
    storage.new_queue(queue, token, domain)
    return {'queue': request.route_url('/queue/{queue}/', queue=queue)}


def queue_has_token(request):
    storage = request.registry['storage']
    queue = request.matchdict['queue']
    user = storage.get_user_for_queue(queue)
    if not user:
        return 404, 'Not Found'

    request.validated['user'] = user


@messages.post(validators=queue_has_token)
def new_message(request):
    """Add a new message to the queue."""
    queuey = request.registry['queuey']
    queue = request.matchdict['queue']
    body = dict(request.POST)
    token = request.validated['user']

    response = queuey.new_message(queue, json.dumps(body))
    message = response['messages'][0]
    pub = {'timestamp': message['timestamp'],
           'key': message['key'],
           'queue': queue,
           'body': body}
    publish(request, token, pub)
    return response


def publish(request, token, message):
    """Publish the message over pubsub on the token's channel."""
    global PUSH_SOCKET
    if PUSH_SOCKET is None:
        PUSH_SOCKET = zmq.Context().socket(zmq.PUSH)
        PUSH_SOCKET.connect(request.registry.settings['zeromq.push'])
    msg = ('PUSH', token, json.dumps(message))
    PUSH_SOCKET.send_multipart(msg)


def check_token(request):
    """The queue must be requested with a matching device token."""
    if 'x-auth-token' not in request.headers:
        return 400, 'An X-Auth-Token header must be included.'

    token = request.headers['x-auth-token']
    storage = request.registry['storage']

    if not storage.user_owns_queue(token, request.matchdict['queue']):
        return 404, 'Not Found.'


@messages.get(validators=check_token)
def get_messages(request):
    """Fetch messages from the queue, most recent first."""
    queuey = request.registry['queuey']
    queue = request.matchdict['queue']

    kwargs = {'order': 'ascending',
              'limit': min(20, request.GET.get('limit', 20))}
    if 'since' in request.GET:
        kwargs['since'] = request.GET['since']
    messages = []
    for message in queuey.get_messages(queue, **kwargs):
        messages.append({'queue': queue,
                         'body': json.loads(message['body']),
                         'key': message['message_id'],
                         'timestamp': message['timestamp']})
    return {'messages': messages}



@nodes.get()
def get_nodes(request):
    storage = request.registry['storage']
    return {'nodes': storage.get_edge_nodes(5)}
