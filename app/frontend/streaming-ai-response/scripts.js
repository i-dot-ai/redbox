// @ts-check

class websocketStream extends HTMLElement {

    stream = () => {
        
        let url = this.dataset.url;
        if (!url) {
            return;
        }
        let webSocket = new WebSocket(url);

        // create new p element
        let el = document.createElement('p');
        this.appendChild(el);

        webSocket.onopen = (event) => {
            this.dataset.status="streaming";
        };

        webSocket.onerror = (event) => {
            this.dataset.status="error";
        };

        webSocket.onclose = (event) => {
            this.dataset.status="error";
        };

        webSocket.onmessage = (event) => {
            if (event.data !== "[END]") {
                el.textContent += event.data;
            } else {
                this.dataset.status="complete";
            }
        };

    };
  
  }
  customElements.define('websocket-stream', websocketStream);
