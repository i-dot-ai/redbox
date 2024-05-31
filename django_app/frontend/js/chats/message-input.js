// @ts-check

class MessageInput extends HTMLElement {

    connectedCallback() {

        // Submit form on enter-key press (providing shift isn't being pressed)
        const textarea = this.querySelector('textarea');
        textarea?.addEventListener('keypress', (evt) => {
            if (evt.key === 'Enter' && !evt.shiftKey) {
                evt.preventDefault();
                if (textarea.value) {
                    this.closest('form')?.requestSubmit();
                }
            }
        });

    }
  
}
customElements.define('message-input', MessageInput);