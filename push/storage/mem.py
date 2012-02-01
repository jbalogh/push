from collections import defaultdict

from push.storage.base import StorageBase


class Storage(StorageBase):

    def __init__(self, **kw):
        self.db = {'queues': defaultdict(dict),
                   'users': defaultdict(set),
                   'domains': defaultdict(set),
                   'android': {}}

    def new_queue(self, queue, user, domain):
        self.db['queues'][queue] = {'user': user, 'domain': domain}
        self.db['users'][user].add(queue)
        self.db['domains'][domain].add(queue)

    def user_owns_queue(self, user, queue):
        return queue in self.db['users'][user]

    def domain_owns_queue(self, domain, queue):
        return queue in self.db['domains'][domain]

    def get_user_for_queue(self, queue):
        return self.db['queues'][queue].get('user')

    def set_queue_timestamp(self, queue, timestamp):
        self.db['queues'][queue]['timestamp'] = timestamp

    def get_queue_timestamp(self, queue):
        return float(self.db['queues'][queue].get('timestamp', 0))

    def set_android_id(self, user, droid_id):
        self.db['android'][user] = droid_id

    def get_android_id(self, user):
        return self.db['android'][user]
