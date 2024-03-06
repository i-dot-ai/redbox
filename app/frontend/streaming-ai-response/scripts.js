// @ts-check

class websocketStream extends HTMLElement {

  /**
   * @param {string} message
   */
  stream = (message) => {

    let url = this.dataset.url;
    if (!url) {
      return;
    }
    let webSocket = new WebSocket(url);

    webSocket.onopen = (event) => {
      webSocket.send(message);
      this.dataset.status = "streaming";
    };

    webSocket.onerror = (event) => {
      this.dataset.status = "error";
    };
    webSocket.onclose = (event) => {
      this.dataset.status = "complete";
    };

    // create a <p> element for content to go into
    this.innerHTML = "<p></p>";

    webSocket.onmessage = (event) => {
      const newText = event.data.replace(/\n/g, "</p><p>");
      this.innerHTML = this.innerHTML.replace(/<\/p>$/, `${newText}</p>`);
    };

  };

}
customElements.define('websocket-stream', websocketStream);
