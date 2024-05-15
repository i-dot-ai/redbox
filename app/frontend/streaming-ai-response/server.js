let WebSocketServer = require('ws').WebSocketServer;

const WORDS = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.".split(' ');
const INTERVAL_MS = 100;
const ws = new WebSocketServer({ port: 8888 });

ws.on('connection', function connection(ws) {

  ws.on('error', console.error);

  ws.on('message', function message(data) {
    console.log('Received: %s', data);
  });

  console.log('Websocket open');

  const totalWords = Math.random() * 100;
  let wordCount = 0;
  const sendWord = () => {

    let toSend = '';
    const numberOfWordsToSend = Math.floor(Math.random() * 3);

    for (let i = 0; i < numberOfWordsToSend; i++) {
      let word = WORDS[Math.floor(Math.random() * WORDS.length)];
      // Add a random **bold markdown** occasionally - to test markdown -> HTML conversion
      if (word.indexOf('.') !== -1 && Math.random() > 0.5) {
        word = `**${word}**`;
      }
      // Add a random paragraph/new-line occasionally
      if (word.indexOf('.') !== -1 && Math.random() > 0.5) {
        word = word + '\n\n';
      }
      toSend += `${word} `;
    }

    ws.send(`${toSend} `);

    wordCount++;
    if (wordCount < totalWords) {
      setTimeout(sendWord, INTERVAL_MS);
    } else {
      ws.close();
    }
  };
  sendWord();

});
