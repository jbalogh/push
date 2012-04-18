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

    def delete_queue(self, user, queue):
        if queue in self.db['queues']:
            del self.db['queues'][queue]
            self.db['users'][user].remove(queue)

    def get_queues(self, user):
        rv = {}
        for queue in self.db['users'][user]:
            domain = self.db['queues'][queue]['domain']
            rv[domain] = queue
        return rv

    def user_owns_queue(self, user, queue):
        return queue in self.db['users'][user]

    def domain_owns_queue(self, domain, queue):
        return queue in self.db['domains'][domain]

    def get_user_for_queue(self, queue):
        return self.db['queues'][queue].get('user')

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
