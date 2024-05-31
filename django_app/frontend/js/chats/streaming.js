// @ts-check

class SourcesList extends HTMLElement {

    constructor() {
        super();
        this.sources = [];
    }

    /**
     * Adds a source to the current message
     * @param {string} fileName 
     * @param {string} url 
     */
    add = (fileName, url) => {
        
        this.sources.push({
            fileName: fileName,
            url: url
        });

        let html = `
            <h3 class="iai-chat-message__sources-heading govuk-heading-s govuk-!-margin-bottom-1">Sources</h3>
            <ul class="govuk-list govuk-list--bullet govuk-!-margin-bottom-0">
        `;
        this.sources.forEach((source) => {
            html += `
                <li class="govuk-!-margin-bottom-0">
                    <a class="iai-chat-messages__sources-link govuk-link" href="${source.url}">${source.fileName}</a>
                </li>
            `;
        });
        html += `</ul>`;
    
        this.innerHTML = /** @type {any} */ (DOMPurify.sanitize(html, {
            RETURN_TRUSTED_TYPE: true
        }));

    }

}
customElements.define('sources-list', SourcesList);




class ChatMessage extends HTMLElement {

    connectedCallback() {
        const html = `
            <div class="iai-chat-message iai-chat-message--${this.dataset.role} govuk-body">
                <div class="iai-chat-message__role">${this.dataset.role === 'ai' ? 'Redbox' : 'You'}</div>
                ${!this.dataset.text ?
                    `<div class="iai-streaming-response-loading js-streaming-response-loading govuk-!-margin-top-1" tabindex="-1">
                        <img class="iai-streaming-response-loading__spinner" src="/static/images/spinner.gif" alt=""/>
                        <p class="iai-streaming-response-loading__text govuk-body-s govuk-!-margin-bottom-0 govuk-!-margin-left-1">Response loading...</p>
                    </div>`
                : ''}
                <markdown-converter class="iai-chat-message__text">${this.dataset.text || ''}</markdown-converter>
                <sources-list></sources-list>
            </div>
        `;
        this.innerHTML = /** @type {any} */ (DOMPurify.sanitize(html, {
            RETURN_TRUSTED_TYPE: true,
            CUSTOM_ELEMENT_HANDLING: {
                tagNameCheck: (tagName) => tagName === 'markdown-converter' || tagName === 'sources-list',
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
     * @param {HTMLElement} chatControllerRef
     */
    stream = (message, sessionId, endPoint, chatControllerRef) => {

        let responseContainer = /** @type MarkdownConverter */(this.querySelector('markdown-converter'));
        let sourcesContainer = /** @type SourcesList */(this.querySelector('sources-list'));
        let responseLoading = /** @type HTMLElement */(this.querySelector('.js-streaming-response-loading'));
        let webSocket = new WebSocket(endPoint);
        let streamedContent = '';
        let sources = [];
    
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
            
            let message;
            try {
                message = JSON.parse(event.data);
            } catch(err) {
                console.log('Error getting JSON response', err);
            }

            if (message.type === 'text') {
                responseLoading.style.display = 'none';
                streamedContent += message.data;
                responseContainer.update(streamedContent);
            } else if (message.type === 'session-id') {
                chatControllerRef.dataset.sessionId = message.data;
            } else if (message.type === 'source') {
                sourcesContainer.add(message.data.original_file_name, message.data.url);
            }
            
        };
    
    };

}
customElements.define('chat-message', ChatMessage);




class ChatController extends HTMLElement {

    connectedCallback() {

        const messageForm = this.querySelector('.js-message-input');
        const textArea = /** @type {HTMLInputElement | null} */ (this.querySelector('.js-user-text'));
        const messageContainer = this.querySelector('.js-message-container');
        const insertPosition = this.querySelector('.js-response-feedback');
        const feedbackButtons = /** @type {HTMLElement | null} */ (this.querySelector('feedback-buttons'));

        messageForm?.addEventListener('submit', (evt) => {
            
            evt.preventDefault();
            const userText = textArea?.value.trim();
            if (!textArea || !userText) {
                return;
            }

            let userMessage = document.createElement('chat-message');
            userMessage.setAttribute('data-text', userText);
            userMessage.setAttribute('data-role', 'user');
            messageContainer?.insertBefore(userMessage, insertPosition);

            let aiMessage = /** @type {ChatMessage} */ (document.createElement('chat-message'));
            aiMessage.setAttribute('data-role', 'ai');
            aiMessage.setAttribute('tabindex', '-1');
            messageContainer?.insertBefore(aiMessage, insertPosition);
            aiMessage.stream(userText, this.dataset.sessionId, this.dataset.streamUrl || '', this);
            aiMessage.focus();

            // reset UI 
            if (feedbackButtons) {
                feedbackButtons.dataset.status = "";
            }
            textArea.value = "";

        });

    }
  
}
customElements.define('chat-controller', ChatController);
