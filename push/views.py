import json

from pyramid.httpexceptions import HTTPNotFound
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
            request.errors.add('body', key, 'Missing required parameter.')


@queues.post(validators=has_token_and_domain)
def new_queue(request):
    """Create a new queue between the given user and domain."""
    queuey = request.registry['queuey']
    storage = request.registry['storage']

    queue = queuey.new_queue()
    token, domain = request.POST['token'], request.POST['domain']
    storage.new_queue(queue, token, domain)
    return {'queue': request.route_url('/queue/{queue}/', queue=queue)}


def has_token(request):
    if not request.GET.get('token'):
        request.errors.add('body', 'token', 'Missing required parameter.')


@queues.get(validators=has_token)
def get_queues(request):
    """Get all of the user's queues."""
    storage = request.registry['storage']
    return dict((k, request.route_url('/queue/{queue}/', queue=v))
                for k, v in storage.get_queues(request.GET['token']).items())


@messages.delete(validators=has_token)
def delete_queue(request):
    queuey = request.registry['queuey']
    storage = request.registry['storage']

    token = request.GET['token']
    queue = request.matchdict['queue']
    if not (token and storage.user_owns_queue(token, queue)):
        return HTTPNotFound()

    queuey.delete_queue(queue)
    storage.delete_queue(token, queue)
    return {'queue': request.route_url('/queue/{queue}/', queue=queue)}


@messages.post()
def new_message(request):
    """Add a new message to the queue."""
    queuey = request.registry['queuey']
    storage = request.registry['storage']

    queue = request.matchdict['queue']
    token = storage.get_user_for_queue(queue)
    if not token:
        return HTTPNotFound()

    body = dict(request.POST)

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


@messages.get(validators=has_token)
def get_messages(request):
    """Fetch messages from the queue, most recent first."""
    queuey = request.registry['queuey']
    storage = request.registry['storage']

    queue = request.matchdict['queue']
    token = request.GET['token']
    if not storage.user_owns_queue(token, queue):
        return HTTPNotFound()

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
