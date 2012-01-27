import json

import redis
from cornice.service import Service


tokens = Service(name='tokens', path='/token/')
queues = Service(name='queues', path='/queue/')
messages = Service(name='messages', path='/queue/{queue}/')
android = Service(name='android', path='/android/')


def has_token_and_registration_id(request):
    "Non-empty token and registration_id values must be give in the POST body."
    for key in ('token', 'registration_id'):
        if not request.POST.get(key):
            return 400, 'Missing required argument: ' + key


@android.post(validators=has_token_and_registration_id)
def add_droid_id(request):
    """Sync an Android device ID with a push token."""
    storage = request.registry['storage']
    user = request.POST['token']
    droid_id = request.POST['registration_id']
    storage.set_android_id(user, droid_id)
    return {'ok': 'ok'}


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
    body = json.dumps(dict(request.POST))
    token = request.validated['user']

    response = queuey.new_message(queue, body)
    pub = json.dumps({'timestamp': response['timestamp'],
                      'key': response['key'],
                      'queue': queue,
                      'body': body})
    redis.Redis().publish('push.' + token, pub)
    return response


def valid_float(request):
    if 'timestamp' not in request.POST:
        return 400, 'Need a `timestamp` parameter.'
    try:
        float(request.POST['timestamp'])
    except (ValueError, TypeError):
        return 400, '`timestamp` must be a float.'


@messages.put(validators=(queue_has_token, valid_float))
def add_timestamp(request):
    storage = request.registry['storage']
    queue = request.matchdict['queue']
    timestamp = request.POST['timestamp']
    storage.set_queue_timestamp(queue, timestamp)
    return {}


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
    storage = request.registry['storage']
    queue = request.matchdict['queue']

    kwargs = {'order': 'ascending',
              'limit': min(20, request.GET.get('limit', 20))}
    if 'since' in request.GET:
        kwargs['since'] = request.GET['since']
    return {'messages': queuey.get_messages(queue, **kwargs),
            'last_seen': storage.get_queue_timestamp(queue)}
