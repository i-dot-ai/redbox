// @ts-check

// Improving the UX for non-streaming responses

// check if a new response is available
(() => {
    
    if (window.sessionStorage.getItem('new-response') === 'true') {
        window.sessionStorage.removeItem('new-response');
        const responses = /** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll('.js-message-container > .js-chat-message'));
        window.setTimeout(() => {
            responses[responses.length - 1].focus();
        }, 100);
    }

    // show loading message when button is clicked
    document.querySelector('.js-message-input')?.addEventListener('submit', (evt) => {      
        let textBox = /** @type {HTMLInputElement} */ (document.querySelector('.js-user-text'));
        if (!textBox.value) {
            return;
        }
        const loadingMessage = /** @type {HTMLElement} */ (document.querySelector('.js-response-loading'));
        loadingMessage.style.visibility = 'visible';
        window.sessionStorage.setItem('new-response', 'true');
        window.setTimeout(() => {
            loadingMessage.focus();
        }, 100);
    });

})();