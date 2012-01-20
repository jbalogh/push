import redis

from push.storage.base import StorageBase


class Storage(StorageBase):
    q = 'push:q:1:'  # Queues.
    u = 'push:u:1:'  # Users.
    d = 'push:d:1:'  # Domains.
    k = 'push:k:1:'  # API keys.
    a = 'push:a:1:'  # Android tokens.

    def __init__(self, **kw):
        self.redis = redis.Redis(**kw)

    def new_queue(self, queue, user, domain):
        self.redis.hmset(self.q + queue, {'user': user, 'domain': domain})
        self.redis.sadd(self.u + user, queue)
        self.redis.sadd(self.d + domain, queue)

    def user_owns_queue(self, user, queue):
        return self.redis.sismember(self.u + user, queue)

    def domain_owns_queue(self, domain, queue):
        return self.redis.sismember(self.d + domain, queue)

    def new_api_key(self, domain, key):
        self.redis.hmset(self.k, key, domain)

    def get_domain_by_key(self, key):
        return self.redis.hget(self.k, key)

    def get_user_for_queue(self, queue):
        return self.redis.hget(self.q + queue, 'user')

    def set_queue_timestamp(self, queue, timestamp):
        self.redis.hset(self.q + queue, 'timestamp', timestamp)

    def get_queue_timestamp(self, queue):
        return float(self.redis.hget(self.q + queue, 'timestamp') or 0)

    def set_android_id(self, user, droid_id):
        return self.redis.set(self.a + user, droid_id)

    def get_android_id(self, user):
        return self.redis.get(self.a + user)
