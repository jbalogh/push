from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (joinedload, relationship,
                            scoped_session, sessionmaker)

from push.storage.base import StorageBase

Session = scoped_session(sessionmaker())
ModelBase = declarative_base()


class User(ModelBase):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    token = Column(String(255), unique=True)

    def __init__(self, token):
        self.token = token

    @classmethod
    def get_or_create(self, token):
        user = Session.query(User).filter_by(token=token).first()
        if user is None:
            user = User(token=token)
            Session.add(user)
            Session.commit()
        return user


class Queue(ModelBase):
    __tablename__ = 'queues'
    id = Column(Integer, primary_key=True)
    queue = Column(String(255), index=True)
    domain = Column(String(255))

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User, primaryjoin=user_id == User.id)

    def __init__(self, queue, user, domain):
        self.queue = queue
        self.user = user
        self.domain = domain


class Node(ModelBase):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    address = Column(String(255), unique=True)
    num_connections = Column(Integer)

    def __init__(self, address, num_connections):
        self.address = address
        self.num_connections = num_connections


class Storage(StorageBase):

    def __init__(self, sqluri):
        self.engine = create_engine(sqluri)
        Session.configure(bind=self.engine)

    def new_queue(self, queue, user, domain):
        user = User.get_or_create(user)
        queue = Queue(queue, user, domain)
        Session.add(queue)
        Session.commit()

    def get_queues(self, user):
        queues = Session.query(Queue).filter(User.token == user).all()
        rv = {}
        for queue in queues:
            rv[queue.domain] = queue.queue
        return rv

    def get_queue(self, queue):
        queue = (Session.query(Queue).options(joinedload('user'))
                 .filter_by(queue=queue).first())
        if queue:
            return {'user': queue.user.token, 'domain': queue.domain}

    def delete_queue(self, user, queue):
        queue = (Session.query(Queue)
                 .filter(User.token == user, Queue.queue == queue)).first()
        if queue:
            Session.delete(queue)
            Session.commit()

    def user_owns_queue(self, user, queue):
        return self.get_user_for_queue(queue) == user

    def get_user_for_queue(self, queue):
        return (self.get_queue(queue) or {}).get('user')

    def add_edge_node(self, address, num_connections):
        node = Session.query(Node).filter_by(address=address).first()
        if node is None:
            node = Node(address, num_connections)
        Session.add(node)
        Session.commit()

    def get_edge_nodes(self, num=None):
        q = Session.query(Node).order_by(Node.num_connections)
        if num is not None:
            q = q.limit(num)
        return [node.address for node in q.all()]

    def remove_edge_node(self, address):
        node = Session.query(Node).filter_by(address=address).first()
        if node:
            Session.delete(node)
            Session.commit()
