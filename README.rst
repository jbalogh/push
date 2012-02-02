Getting Started
---------------

1. Make your virtualenv.
2. Install the python packages::

    pip install -r dev-reqs.txt

3. Install Queuey from https://github.com/mozilla-services/queuey.

4. Start the server::

    paster serve etc/push-dev.ini


Run the Server
--------------
::

    paster serve etc/push-dev.ini


Public API
----------

::

    POST /queue/<queue>/

    Add a new message to the queue.

    Parameters:
    * iconUrl: URL of the icon to be shown with this notification.
    * title: Primary text of the notification.
    * body: Secondary text of the notification.
    * actionUrl: URL to be opened if the user clicks on the notification.
    * replaceId: A string which identifies a group of like messages. If the
      user is offline, only the last message with the same replaceId will be
      sent when the user comes back online.

    Accepted content types:
    * Content-Type: application/x-www-form-urlencoded
    * Content-Type: application/json


Client API
----------

::

    POST /token/

    >>> 200 OK {"token": <token>}

    Create a new token. This token should be stored on the client for future
    authentication.

::

    POST /queue/

    token=<token>&domain=<domain>

    >>> 200 OK {"queue": http://example.com/queue/<queue>/}

    Create a new queue.
    * <token> should be a value created by POSTing to /token/.
    * <domain> is the domain the queue belongs to.

::

    PUT /queue/<queue>/
    X-Auth-Token: <token>

    timestamp=<timestamp>

    Update the <timestamp> of the queue. Used to coordinate with other clients
    on which messages have been read. The <token> used to create the queue must
    be given for authentication.

::

    GET /queue/<queue>/
    X-Auth-Token: <token>

    >>> 200 OK {"messages": [<message>...], "last_seen": <timestamp>}

    Get messages from the queue. The <token> used to create the queue must be
    given for authentication.

    The format of a message:
        TBD

    The `last_seen` parameter gives the latest timestamp a client reported so
    that other clients know which messages have been read.

    Optional query parameters:

    limit: The maximum number of messages to show.
    since: If given, only return messages sent later than `since`.


Android Client API
------------------

::

    POST /android/

    token=<token>&registration_id=<registration_id>

    Connect an authentication token with an Android registration ID. If a token
    has a connected Android ID the server will try to send messages to the
    client over Android C2DM.
