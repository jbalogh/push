import time
import uuid


class Message(object):

    def __init__(self, message):
        self.key = unicode(uuid.uuid4().hex)
        self.value = message
        self.timestamp = time.time()


class MockQueuey(object):

    def __init__(self):
        self.db = {}

    def new_queue(self):
        queue = unicode(uuid.uuid4().hex)
        self.db[queue] = []
        return queue

    def new_message(self, queue, message):
        msg = Message(message)
        self.db[queue].append(msg)
        return {u'key': msg.key,
                u'partition': 1,
                u'status': u'ok',
                u'timestamp': msg.timestamp}

    def get_messages(self, queue, since=None, limit=None, order=None):
        if since:
            rv = [m for m in self.db[queue] if m.timestamp > since]
        else:
            rv = list(self.db[queue])

        # The default is descending order.
        if order != 'ascending':
            rv.reverse()

        if limit:
            rv = rv[:limit]

        return [{u'body': m.value, u'key': m.key, u'timestamp': m.timestamp}
                for m in rv]