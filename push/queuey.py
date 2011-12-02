import json

import requests


class QueueyException(Exception):
    """Exception raised if queuey does not respond with a 200."""


class Queuey(object):

    def __init__(self, url, application_key):
        self.url = url[:-1] if url.endswith('/') else url
        self.application_key = application_key
        self.headers = {'ApplicationKey': self.application_key}

    def request(self):
        return requests.session(headers=self.headers,
                                hooks={'response': self.json_response})

    def json_response(self, response):
        if response.status_code == 200:
            response.json = json.loads(response.content)
        else:
            raise QueueyException(response)

    def new_queue(self):
        response = self.request().post(self.url + '/queue/')
        return response.json['queue_name']

    def new_message(self, queue, message):
        response = self.request().post(self.url + '/queue/%s/' % queue,
                                       data={'message': message})
        return response.json['status'] == 'ok'

    def get_messages(self, queue, since=None, limit=None, order=None):
        keys = ('since_timestamp', 'limit', 'order')
        qs = dict((k, v) for k, v in zip(keys, (since, limit, order)) if v)
        response = self.request().get(self.url + '/queue/%s/' % queue,
                                      params=qs)
        return response.json['messages']
