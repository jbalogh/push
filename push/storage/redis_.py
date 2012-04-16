import redis

from push.storage.base import StorageBase


class Storage(StorageBase):
    q = 'push:q:1:'  # Queues.
    u = 'push:u:1:'  # Users.
    d = 'push:d:1:'  # Domains.
    n = 'push:n:1:'  # Edge node status.

    def __init__(self, **kw):
        self.redis = redis.Redis(**kw)

    def new_queue(self, queue, user, domain):
        self.redis.hmset(self.q + queue, {'user': user, 'domain': domain})
        self.redis.sadd(self.u + user, queue)
        self.redis.sadd(self.d + domain, queue)

    def get_queues(self, user):
        rv = {}
        for queue in self.redis.smembers(self.u + user):
            domain = self.redis.hget(self.q + queue, 'domain')
            rv[domain] = queue
        return rv

    def user_owns_queue(self, user, queue):
        return self.redis.sismember(self.u + user, queue)

    def domain_owns_queue(self, domain, queue):
        return self.redis.sismember(self.d + domain, queue)

    def get_user_for_queue(self, queue):
        return self.redis.hget(self.q + queue, 'user')

    def add_edge_node(self, node, num_connections):
        self.redis.zadd(self.n, node, num_connections)

    def get_edge_nodes(self, num=None):
        """Get edge nodes sorted by ascending number of connections."""
        # If num is None get all of them. Subtract 1 b/c zrange in inclusive.
        num = -1 if num is None else num - 1
        return self.redis.zrange(self.n, 0, num)

    def remove_edge_node(self, node):
        self.redis.zrem(self.n, node)
