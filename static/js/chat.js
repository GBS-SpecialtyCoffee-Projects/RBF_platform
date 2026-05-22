(function () {
    var config = window.CHAT_CONFIG || {};
    if (!config.conversationId) {
        return;
    }

    var $messages = $('#chat-messages');
    var $form = $('#chat-form');
    var $input = $('#chat-input');
    var $status = $('#chat-status');
    var currentUserId = config.currentUserId;

    function scrollToBottom() {
        $messages.scrollTop($messages[0].scrollHeight);
    }

    function escapeHtml(text) {
        return $('<div>').text(text).html();
    }

    function formatTime(iso) {
        var d = new Date(iso);
        return d.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    }

    function appendMessage(msg) {
        var mine = msg.sender_id === currentUserId;
        var bubbleClasses = mine ? 'bg-primary text-white' : 'bg-light text-dark';
        var rowClasses = mine ? 'justify-content-end' : 'justify-content-start';
        var stampClasses = mine ? 'text-white-50' : 'text-muted';
        var body = escapeHtml(msg.body).replace(/\n/g, '<br>');
        var html = '<div class="d-flex mb-2 ' + rowClasses + '">' +
                   '<div class="px-3 py-2 rounded ' + bubbleClasses + '" style="max-width: 75%; word-wrap: break-word;">' +
                   body +
                   '<div class="small ' + stampClasses + '" style="font-size: 0.7rem;">' + formatTime(msg.created_at) + '</div>' +
                   '</div></div>';
        $messages.append(html);
        scrollToBottom();
    }

    var socket = null;
    var reconnectAttempts = 0;

    function connect() {
        var protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        var url = protocol + window.location.host + '/ws/chat/' + config.conversationId + '/';
        socket = new WebSocket(url);

        socket.onopen = function () {
            reconnectAttempts = 0;
            $status.text('Connected');
            setTimeout(function () { $status.text(''); }, 1500);
        };

        socket.onmessage = function (event) {
            var data = JSON.parse(event.data);
            appendMessage(data);
        };

        socket.onclose = function (event) {
            if (event.code === 4401 || event.code === 4403) {
                $status.text('Not authorized for this conversation.');
                return;
            }
            $status.text('Disconnected. Reconnecting...');
            reconnectAttempts += 1;
            var delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 15000);
            setTimeout(connect, delay);
        };

        socket.onerror = function () {
            $status.text('Connection error');
        };
    }

    $form.on('submit', function (e) {
        e.preventDefault();
        var body = $input.val().trim();
        if (!body) return;
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            $status.text('Not connected. Wait a moment and try again.');
            return;
        }
        socket.send(JSON.stringify({ body: body }));
        $input.val('');
    });

    scrollToBottom();
    connect();
})();
