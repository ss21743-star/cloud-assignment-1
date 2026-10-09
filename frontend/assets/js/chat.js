
var checkout = {};

$(document).ready(function() {

  var $messages = $('.messages-content');
  var d, m;
  var i = 0;

  // Your deployed API Gateway endpoint
  var API_URL =
    'https://wj83v6r5ge.execute-api.us-east-1.amazonaws.com/prod/chatbot';

  // Maintain the same Lex session across messages
  var sessionId =
    'web-' + Date.now() + '-' +
    Math.random().toString(36).substring(2, 10);

  // Initialize chat interface
  $(window).on('load', function() {
    $messages.mCustomScrollbar();

    insertResponseMessage(
      "Hi there, I'm your personal Concierge. How can I help?"
    );
  });

  // Scroll to latest message
  function updateScrollbar() {
    $messages
      .mCustomScrollbar("update")
      .mCustomScrollbar('scrollTo', 'bottom', {
        scrollInertia: 10,
        timeout: 0
      });
  }

  // Display timestamp
  function setDate() {
    d = new Date();

    if (m !== d.getMinutes()) {
      m = d.getMinutes();

      $('<div class="timestamp">' +
        d.getHours() + ':' +
        String(m).padStart(2, '0') +
        '</div>')
        .appendTo($('.message:last'));
    }
  }

  // Send user message to API Gateway -> LF0 -> Lex
  function callChatbotApi(message) {

    return $.ajax({
      url: API_URL,
      method: 'POST',
      contentType: 'application/json',
      dataType: 'json',

      data: JSON.stringify({
        sessionId: sessionId,

        messages: [{
          type: 'unstructured',
          unstructured: {
            text: message
          }
        }]
      })
    }).then(function(data) {

      console.log('API response:', data);

      // Preserve Lex session
      if (data.sessionId) {
        sessionId = data.sessionId;
      }

      // Match existing response handler
      return { data: data };
    });
  }

  // Handle user message
  function insertMessage() {

    var msg = $('.message-input').val();

    if ($.trim(msg) === '') {
      return false;
    }

    // Show user message
    $('<div class="message message-personal"></div>')
      .text(msg)
      .appendTo($('.mCSB_container'))
      .addClass('new');

    setDate();

    $('.message-input').val('');

    updateScrollbar();

    // Call AWS chatbot API
    callChatbotApi(msg)

      .then(function(response) {

        console.log(response);

        var data = response.data;

        if (data.messages && data.messages.length > 0) {

          for (var message of data.messages) {

            if (message.type === 'unstructured') {

              insertResponseMessage(
                message.unstructured.text
              );

            } else {

              console.log(
                'Unsupported message type:',
                message
              );

            }
          }

        } else {

          insertResponseMessage(
            'Oops, something went wrong. Please try again.'
          );

        }
      })

      .catch(function(error) {

        console.error('Chatbot API error:', error);

        insertResponseMessage(
          'Oops, something went wrong. Please try again.'
        );

      });

    return true;
  }

  // Send button
  $('.message-submit').click(function() {
    insertMessage();
  });

  // Enter key
  $(window).on('keydown', function(e) {

    if (
      e.which === 13 &&
      $(e.target).is('.message-input')
    ) {
      insertMessage();
      return false;
    }
  });

  // Display chatbot response
  function insertResponseMessage(content) {

    var avatar =
      'https://media.tenor.com/images/' +
      '4c347ea7198af12fd0a66790515f958f/tenor.gif';

    var $loading = $(
      '<div class="message loading new">' +
        '<figure class="avatar">' +
          '<img src="' + avatar + '" />' +
        '</figure>' +
        '<span></span>' +
      '</div>'
    );

    $loading.appendTo($('.mCSB_container'));

    updateScrollbar();

    setTimeout(function() {

      $loading.remove();

      var $response = $(
        '<div class="message new">' +
          '<figure class="avatar">' +
            '<img src="' + avatar + '" />' +
          '</figure>' +
        '</div>'
      );

      $response.append(document.createTextNode(content));

      $response
        .appendTo($('.mCSB_container'))
        .addClass('new');

      setDate();
      updateScrollbar();

      i++;

    }, 500);
  }

});
