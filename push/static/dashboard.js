/*jshint browser:true jquery:true curly:true noarg:true trailing:true */
/*global console _ */

(function() {
"use strict";

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
    var data = JSON.parse(e.data);
    data.body = JSON.parse(data.body);
    var queue = _.find(_.values(findQueues()),
                       function(q){ return q.indexOf(data.queue) !== -1; });
    updateQueueTimestamp(queue, data.timestamp);
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
    $.post('://' + location.host + '/token/', function(response) {
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


function updateQueueTimestamp(queue, timestamp) {
  log('update', queue, timestamp);
  // localStorage[queue] = timestamp;
  $.ajax({
    type: 'PUT',
    url: queue,
    data: {timestamp: timestamp},
    success: function(){ log('updated timestamp to', timestamp); }
  });
}


function messageHandler(queue) {
  return function(response) {
    if (response.messages.length) {
      // Convert the messages to JSON.
      _.each(response.messages,
             function(e){ e.body = JSON.parse(e.body); });

      // Update the queue's timestamp.
      var timestamps = _.pluck(response.messages, 'timestamp');
      updateQueueTimestamp(queue, Math.max.apply(null, timestamps));

      log(response.last_seen);
      var latest = Math.max(response.last_seen, localStorage[queue]);
      log('latest', new Date(latest * 1000));

      // Render the new messages.
      _.each(response.messages, function(m) {
        m.visited = m.timestamp <= latest;
        addMessage(m);
      });
    }
  };
}


function getMessages(token) {
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
      success: messageHandler(queue),
      headers: {'x-auth-token': token},
      dataType: 'json'
    });
  }
}


function addMessage(msg) {
  log(msg.body.body, msg.timestamp);
  var cls = msg.visited ? 'old' : 'new',
      s = ('<li class="' + cls + '"><b>' + msg.body.title +
           '</b>(' + new Date(msg.timestamp * 1000) + ')<br>' +
           msg.body.body + '</li>');
  $messages.append(s);
}


var token,
    $messages = $('#messages');

getToken(function(t) {
  token = t;
  $('#token').text('Token: ' + token);
  getMessages(token);
  websocket();
});

})();
