var root = 'http://push.app'; // TODO: change to test cross-domain permissions.

function websocket() {
  var ws = new (window.MozWebSocket || window.WebSocket)('ws://' + location.hostname + ':9999/');
  console.log(ws);
  ws.onopen = function() {
    console.log('open', ws.url);
    log('sending', token);
    ws.send(token);
  };
  ws.onmessage = function(e) {
    console.log('data:', e.data);
    var data = JSON.parse(e.data)
    data.body = JSON.parse(data.body);
    var queue = _.find(_.values(findQueues()),
                       function(q){ return q.indexOf(data.queue) !== -1; });
    localStorage[queue] = data.timestamp;
    addMessage(data);
  };
  ws.onclose = function() {
    console.log('close');
    websocket();
  };
  ws.onerror = function(e) {
    console.log('error');
  };
  return ws;
}

function log() {
  var args = [].slice.call(arguments).join(' ');
  console.log(args);
  document.getElementById('logs').innerHTML += '<li>' + args + '</li>';
}

function getToken(cb) {
  if (!localStorage.token) {
    $.post(root + '/token/', function(response) {
      localStorage.token = response.token;
      return cb(localStorage.token);
    });
  } else {
    cb(localStorage.token);
  }
}

function findQueues() {
  var queues = {};
  for (var i = 0, ii = localStorage.length; i < ii; i++) {
    var key = localStorage.key(i),
        value = localStorage.getItem(key);

    if (key.indexOf('queue:') === 0) {
      var domain = key.split(':').slice(1).join(':');
      queues[domain] = value;
    }
  }
  return queues;
}

function successWrapper(queue, cb) {
  return function(response) {
    if (response.messages.length) {
      _.each(response.messages, function(e) { e.body = JSON.parse(e.body); });
      localStorage[queue] = Math.max.apply(null, _.pluck(response.messages, 'timestamp'));
    }
    cb(response);
  }
}

function getMessages(token, cb) {
  var queues = findQueues();
  for (var domain in queues) {
    var queue = queues[domain],
        since = localStorage.getItem(queue),
        url = queue;
    console.log(queue);
    if (since) {
      url += '?since=' + since;
    }
    log('fetching', url);
    $.ajax({
      url: url,
      success: successWrapper(queue, cb),
      headers: {'x-auth-token': token},
      dataType: 'json',
    });
  }
}

var token,
    $messages = $('#messages');

getToken(function(t) {
  token = t;
  $('#token').text('Token: ' + token);
  getMessages(token, function(response){
    r = response;
    _.each(response.messages, addMessage);
  });
  websocket();
});

function addMessage(msg) {
  s = '<li><b>' + msg.body.title + '</b><br>' + msg.body.body + '</li>';
  $messages.append(s);
}
