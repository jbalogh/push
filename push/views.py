import json

from pyramid.httpexceptions import HTTPNotFound
from tornado import escape
import zmq

from cornice.service import Service

# Process-level singleton zmq pusher socket.
PUSH_SOCKET = None

tokens = Service(name='tokens', path='/token/')
queues = Service(name='queues', path='/queue/')
site_queues = Service(name='site_queues', path='/queue/{queue}/')
nodes = Service(name='nodes', path='/nodes/')


@tokens.post()
def new_token(request):
    """Get a new random, opaque string."""
    queuey = request.registry['queuey']
    storage = request.registry['storage']
    token = storage.new_token()
    queuey.new_queue(queue_name=token)
    return {'token': token,
            'queue': request.route_url('/queue/{queue}/', queue=token)}


def has_token_and_domain(request):
    """Non-empty token and domain values must be give in the POST body."""
    for key in ('token', 'domain'):
        if not request.POST.get(key):
            request.errors.add('body', key, 'Missing required parameter.')


@queues.post(validators=has_token_and_domain)
def new_queue(request):
    """Create a new queue between the given user and domain."""
    storage = request.registry['storage']

    queue = storage.new_token()
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


@site_queues.delete(validators=has_token)
def delete_queue(request):
    storage = request.registry['storage']

    token = request.GET['token']
    queue = request.matchdict['queue']
    if not (token and storage.user_owns_queue(token, queue)):
        return HTTPNotFound()

    storage.delete_queue(token, queue)
    return {'queue': request.route_url('/queue/{queue}/', queue=queue)}


def message_validator(request):
    # Abort message validation if we're marking a message as read.
    if request.POST.get('action') == 'read':
        return

    # Try to get the body as form-urlencoded or json.
    body = None
    if request.POST:
        body = dict(request.POST)
    else:
        try:
            body = request.json_body
        except Exception:
            pass

    if not body:
        msg = 'Request could not be decoded as json or form-urlencoded.'
        return request.errors.add('body', 'body', msg)

    # These are the keys we'll accept for messages.
    VALID_KEYS = 'title', 'body', 'actionUrl', 'replaceId'
    request.validated['message'] = dict((k, v) for k, v in body.items()
                                        if k in VALID_KEYS)


@site_queues.post(validators=message_validator)
def new_message(request):
    """Add a new message to the queue."""
    if request.POST.get('action') == 'read':  # How lame is this?
        return mark_message_read(request)

    queuey = request.registry['queuey']
    storage = request.registry['storage']

    queue = request.matchdict['queue']
    token = storage.get_user_for_queue(queue)
    if not token:
        return HTTPNotFound()

    body = request.validated['message']
    json_body = json.dumps({'queue': queue, 'body': body})

    # Add it to the users's queue.
    response = queuey.new_message(token, json_body)
    message = response['messages'][0]
    pub = {'timestamp': message['timestamp'],
           'key': message['key'],
           'queue': request.route_url('/queue/{queue}/', queue=queue),
           'body': body}
    publish(request, token, pub)
    return response


def mark_message_read(request):
    key = request.POST.get('key')
    if not key:
        return HTTPNotFound()

    queuey = request.registry['queuey']
    queue = request.matchdict['queue']

    body = {'read': key}
    json_body = json.dumps({'queue': queue, 'body': body})
    response = queuey.new_message(queue, json_body)
    message = response['messages'][0]
    pub = {'timestamp': message['timestamp'],
           'key': message['key'],
           'queue': request.route_url('/queue/{queue}/', queue=queue),
           'body': body}
    publish(request, queue, pub)
    return response


def publish(request, token, message):
    """Publish the message over pubsub on the token's channel."""
    global PUSH_SOCKET
    if PUSH_SOCKET is None:
        PUSH_SOCKET = zmq.Context().socket(zmq.PUSH)
        PUSH_SOCKET.connect(request.registry.settings['zeromq.push'])
    msg = ('PUSH', escape.utf8(token), json.dumps(message))
    PUSH_SOCKET.send_multipart(msg)


@site_queues.get()
def get_messages(request):
    """Fetch messages from the queue, most recent first."""
    queuey = request.registry['queuey']
    queue = request.matchdict['queue']

    kwargs = {'order': 'ascending',
              'limit': min(20, request.GET.get('limit', 20))}
    if 'since' in request.GET:
        kwargs['since'] = request.GET['since']
    try:
        messages = queuey.get_messages(queue, **kwargs)
    except Exception:
        return HTTPNotFound()

    rv = []
    for message in messages:
        body = json.loads(message['body'])
        rv.append({'body': body['body'],
                   'queue': body['queue'],
                   'queue': request.route_url('/queue/{queue}/',
                                              queue=body['queue']),
                   'key': message['message_id'],
                   'timestamp': message['timestamp']})
    return {'messages': rv}


@nodes.get()
def get_nodes(request):
    storage = request.registry['storage']
    return {'nodes': storage.get_edge_nodes(5)}
