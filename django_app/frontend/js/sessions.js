// @ts-check

/** @type {import ('../node_modules/@types/dompurify/index.d.ts')} */
let DOMPurify = window["DOMPurify"];


class ChatMessage extends HTMLElement {

    connectedCallback() {
        const html = `
            <div class="iai-chat-message iai-chat-message--${this.dataset.role} govuk-body">
                <div class="iai-chat-message__role">${this.dataset.role?.toUpperCase()}</div>
                <div class="iai-chat-message__text js-ai-response">${this.dataset.text || ''}</div>
            </div>
        `;
        this.innerHTML = /** @type {any} */ (DOMPurify.sanitize(html, {RETURN_TRUSTED_TYPE: true}));
    }

    /**
     * Streams an LLM response
     * @param {string} message
     * @param {string | undefined} sessionId
     * @param {string} endPoint
     */
    stream = (message, sessionId, endPoint) => {

        let responseContainer = /** @type {HTMLElement} */ (this.querySelector('.js-ai-response'));
        let webSocket = new WebSocket(endPoint);
        let streamedHtml = '<p></p>';
    
        webSocket.onopen = (event) => {
            webSocket.send(JSON.stringify({message: message, sessionId: sessionId}));
            this.dataset.status = "streaming";
        };
    
        webSocket.onerror = (event) => {
            responseContainer.innerHTML = 'There was a problem. Please try sending this message again.';
            this.dataset.status = "error";
        };

        webSocket.onclose = (event) => {
            this.dataset.status = "complete";
        };
    
        webSocket.onmessage = (event) => {
            const newText = event.data.replace(/\n/g, "</p><p>");
            streamedHtml = streamedHtml.replace(/<\/p>$/, `${newText}</p>`);
            responseContainer.innerHTML = /** @type {any} */ (DOMPurify.sanitize(streamedHtml, {RETURN_TRUSTED_TYPE: true}));
        };
    
    };

}
customElements.define('chat-message', ChatMessage);




class ChatController extends HTMLElement {

    connectedCallback() {

        const sendButton = this.querySelector('.js-send-btn');
        const textArea = /** @type {HTMLInputElement | null} */ (this.querySelector('.js-user-text'));
        const messageContainer = this.querySelector('.js-message-container');
        const insertPosition = this.querySelector('.js-response-feedback');

        sendButton?.addEventListener('click', (evt) => {
            
            evt.preventDefault();
            const userText = textArea?.value;
            if (!userText) {
                return;
            }

            let userMessage = document.createElement('chat-message');
            userMessage.setAttribute('data-text', userText);
            userMessage.setAttribute('data-role', 'user');
            messageContainer?.insertBefore(userMessage, insertPosition);

            let aiMessage = /** @type {ChatMessage} */ (document.createElement('chat-message'));
            aiMessage.setAttribute('data-role', 'ai');
            messageContainer?.insertBefore(aiMessage, insertPosition);
            aiMessage.stream(userText, this.dataset.sessionId, this.dataset.streamUrl || '');

        });

    }
  
}
customElements.define('chat-controller', ChatController);
