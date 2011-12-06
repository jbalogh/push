/* Depends on jschannel.js */
;(function() {
  if (navigator.notifications) {
    return;
  }

  /* Communication frame with jschannel. */
  var frame = document.createElement('iframe');
  frame.id = 'child';
  frame.src = 'http://push.app/child.html#' + document.location.host;
  frame.style.height = '400px';
  frame.style.width = '250px';
  document.body.appendChild(frame);

  var channel = Channel.build({window: frame.contentWindow, origin: '*',
                               scope: 'push', onReady: onReady});
  function onReady() {
    console.log('channel ready');
  }

  /** navigator.notifications shim */
  navigator.notifications = {};

  navigator.notifications.requestPermission = function(cb) {
    var site = location.host;
    if (window.confirm('Allow push notifications for ' + site + '?')) {
        channel.call({method: 'requestPermission',
                      success: cb,
                      error: function(e, m){ console.log(e, m) }});
    }
  };
})();
