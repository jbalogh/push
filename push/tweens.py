import logging

log = logging.getLogger(__name__)


def dump_request(request):
    s = '\n\n%s %s\n' % (request.method, request.url)
    s += '\n'.join('%s: %s' % x for x in sorted(request.headers.items()))
    if request.body:
        s += '\n\n' + request.body
    return s + '\n'


def dump_response(response):
    s = '\n\nHTTP/1.0 ' + response.status + '\n'
    s += '\n'.join('%s: %s' % x for x in sorted(response.headers.items()))
    if response.text:
        if len(response.text) > 256:
            s += '\n\n' + response.text[:256] + '...'
        else:
            s += '\n\n' + response.text
    return s + '\n'


def logger_tween_factory(handler, registry):
    def logger_tween(request):
        out = dump_request(request)
        try:
            response = handler(request)
            log.info(out + dump_response(response))
        except:
            log.error(out + '%s %s (500)' % (request.method, request.url))
            raise
        return response
    return logger_tween
