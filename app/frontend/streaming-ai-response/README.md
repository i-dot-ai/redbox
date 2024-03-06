# Streaming AI Response Component

This is a component to handle a streamed response using websockets. It is built using web components so it can be used interchangeably between projects and work with any frontend framework/library.


## Running the demo

Ensure you have Node.js installed. Then, within the streaming-ai-response folder, run:
`npm install`

To start server:
`node server.js`

Open the static index.html page in a browser. It's fine to use the file:// protocol, and doesn't need to be served from anywhere.


## Using the component in projects

* Add the `scripts.js` file to your page
* Create a `<websocket-stream data-url="ws://[websocket-url]">` element at the point that it's needed, ensuring you set the data-url attribute to the websocket address.
* Call `websocketElement.stream("Message to send to server")`.
* Repeat the process for subsequent messages, adding a new `<websocket-stream>` element.