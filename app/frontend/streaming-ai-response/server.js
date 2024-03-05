let WebSocketServer = require('ws').WebSocketServer;

const WORDS = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.".split(' ');
const INTERVAL_MS = 100;
const ws = new WebSocketServer({ port: 8888 });

ws.on('connection', function connection(ws) {
    ws.on('error', console.error);

    ws.on('message', function message(data) {
        console.log('received: %s', data);
    });

    console.log('Websocket open');
    const totalWords = Math.random() * 100;
    let wordCount = 0;
    const sendWord = () => {
        let word = WORDS[Math.floor(Math.random() * WORDS.length)];
        ws.send(`${word} `);
        wordCount++;
        if (wordCount < totalWords) {
            setTimeout(sendWord, INTERVAL_MS);
        } else {
            ws.send('[END]');
        }
    };
    sendWord();

});
