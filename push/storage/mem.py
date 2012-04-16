from collections import defaultdict

from push.storage.base import StorageBase


class Storage(StorageBase):

    def __init__(self, **kw):
        self.db = {'queues': defaultdict(dict),
                   'users': defaultdict(set),
                   'domains': defaultdict(set),
                   'nodes': {}}

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
        current = self.get_queue_timestamp(queue)
        self.db['queues'][queue]['timestamp'] = max(current, timestamp)

    def get_queue_timestamp(self, queue):
        return float(self.db['queues'][queue].get('timestamp', 0))

    def add_edge_node(self, node, num_connections):
        self.db['nodes'][node] = num_connections

    def get_edge_nodes(self, num=None):
        """Get edge nodes sorted by ascending number of connections."""
        # If num is None get all of them. Subtract 1 b/c zrange in inclusive.
        items = sorted(self.db['nodes'].items(), key=lambda x: x[1])
        nodes = [k for k, v in items]
        return nodes if num is None else nodes[:num]

    def remove_edge_node(self, node):
        if node in self.db['nodes']:
            del self.db['nodes'][node]
