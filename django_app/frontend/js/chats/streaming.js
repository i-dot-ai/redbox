// @ts-check

class ChatMessage extends HTMLElement {

    connectedCallback() {
        const html = `
            <div class="iai-chat-message iai-chat-message--${this.dataset.role} govuk-body">
                <div class="iai-chat-message__role">${this.dataset.role?.toUpperCase()}</div>
                <markdown-converter class="iai-chat-message__text">${this.dataset.text || ''}</markdown-converter>
            </div>
        `;
        this.innerHTML = /** @type {any} */ (DOMPurify.sanitize(html, {
            RETURN_TRUSTED_TYPE: true,
            CUSTOM_ELEMENT_HANDLING: {
                tagNameCheck: (tagName) => tagName === 'markdown-converter',
                attributeNameCheck: (attr) => true,
                allowCustomizedBuiltInElements: true
            }
        }));
    }

    /**
     * Streams an LLM response
     * @param {string} message
     * @param {string | undefined} sessionId
     * @param {string} endPoint
     */
    stream = (message, sessionId, endPoint) => {

        let responseContainer = /** @type MarkdownConverter */(this.querySelector('markdown-converter'));
        let webSocket = new WebSocket(endPoint);
        let streamedContent = '';
    
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
            if (!responseContainer) {
                return;
            }
            streamedContent += event.data;
            responseContainer.update(streamedContent);
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
        const feedbackButtons = /** @type {HTMLElement | null} */ (this.querySelector('feedback-buttons'));

        sendButton?.addEventListener('click', (evt) => {
            
            evt.preventDefault();
            const userText = textArea?.value;
            if (!textArea || !userText) {
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

            // reset UI 
            if (feedbackButtons) {
                feedbackButtons.dataset.status = "";
            }
            textArea.value = "";

        });

    }
  
}
customElements.define('chat-controller', ChatController);
