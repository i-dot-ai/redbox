// @ts-check

class chatMessage extends HTMLElement {

    connectedCallback() {
        const html = `
            <div class="iai-chat-message iai-chat-message--${this.dataset.role} govuk-body">
                <div class="iai-chat-message__role">${this.dataset.role?.toUpperCase()}</div>
                <div class="iai-chat-message__text js-ai-response">${this.dataset.text || ''}</div>
            </div>
        `;
        this.innerHTML = DOMPurify.sanitize(html, {RETURN_TRUSTED_TYPE: true});
    }


    /**
     * @param {string} message
     * @param {string} sessionId
     * @param {string} endPoint
     */
    stream = (message, sessionId, endPoint) => {

        let responseContainer = this.querySelector('.js-ai-response');
        let webSocket = new WebSocket(endPoint);
        let streamedHtml = '<p></p>';
    
        webSocket.onopen = (event) => {
            webSocket.send(JSON.stringify({message: message, sessionId: sessionId}));
            this.dataset.status = "streaming";
        };
    
        webSocket.onerror = (event) => {
            this.dataset.status = "error";
        };
        webSocket.onclose = (event) => {
            this.dataset.status = "complete";
        };
    
        webSocket.onmessage = (event) => {
            if (!responseContainer) {
                return;
            }
            const newText = event.data.replace(/\n/g, "</p><p>");
            streamedHtml = streamedHtml.replace(/<\/p>$/, `${newText}</p>`);
            responseContainer.innerHTML = DOMPurify.sanitize(streamedHtml, {RETURN_TRUSTED_TYPE: true});
        };
    
    };

}
customElements.define('chat-message', chatMessage);




class chatController extends HTMLElement {

    connectedCallback() {

        const sendButton = this.querySelector('.js-send-btn');
        /** @type {HTMLInputElement | null} */
        const textArea = this.querySelector('.js-user-text');
        const messageContainer = this.querySelector('.js-message-container');

        sendButton?.addEventListener('click', (evt) => {
            
            evt.preventDefault();
            const userText = textArea?.value;
            if (!userText) {
                return;
            }

            let userMessage = document.createElement('chat-message');
            userMessage.setAttribute('data-text', userText);
            userMessage.setAttribute('data-role', 'user');
            messageContainer?.appendChild(userMessage);

            let aiMessage = document.createElement('chat-message');
            aiMessage.setAttribute('data-role', 'ai');
            messageContainer?.appendChild(aiMessage);
            aiMessage.stream(userText, this.dataset.sessionId, this.dataset.streamUrl);

        });

    }
  
}
customElements.define('chat-controller', chatController);
