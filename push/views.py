import json

import redis
from cornice.service import Service


tokens = Service(name='tokens', path='/token/')
queues = Service(name='queues', path='/queue/')
messages = Service(name='messages', path='/queue/{queue}/')


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


@queues.post(validator=has_token_and_domain)
def new_queue(request):
    """Create a new queue between the given user and domain."""
    queuey = request.registry['queuey']
    storage = request.registry['storage']

    queue = queuey.new_queue()
    token, domain = request.POST['token'], request.POST['domain']
    storage.new_queue(queue, token, domain)
    return {'queue': request.route_url('/queue/{queue}/', queue=queue)}


def check_api_key(request):
    """The API key must match the domain that set up the queue."""
    if 'x-api-key' not in request.headers:
        return 400, 'An X-API-KEY header must be included.'

    storage = request.registry['storage']
    api_key = request.headers['x-api-key']
    domain = storage.get_domain_by_key(api_key)

    if not storage.domain_owns_queue(domain, request.matchdict['queue']):
        return 404, 'Not Found.'


def queue_has_token(request):
    storage = request.registry['storage']
    queue = request.matchdict['queue']
    user = storage.get_user_for_queue(queue)
    if not user:
        return 404, 'Not Found'

    request.validated['user'] = user


@messages.post(validator=queue_has_token)
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


def check_token(request):
    """The queue must be requested with a matching device token."""
    if 'x-auth-token' not in request.headers:
        return 400, 'An X-Auth-Token header must be included.'

    token = request.headers['x-auth-token']
    storage = request.registry['storage']

    if not storage.user_owns_queue(token, request.matchdict['queue']):
        return 404, 'Not Found.'


@messages.get(validator=check_token)
def get_messages(request):
    """Fetch messages from the queue, most recent first."""
    queuey = request.registry['queuey']
    queue = request.matchdict['queue']

    kwargs = {'order': 'ascending',
              'limit': min(20, request.GET.get('limit', 20))}
    if 'since' in request.GET:
        kwargs['since'] = request.GET['since']
    return {'messages': queuey.get_messages(queue, **kwargs)}
