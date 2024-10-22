// @ts-check

class MessageInput extends HTMLElement {

    constructor() {
        super();
        this.textarea = this.querySelector("textarea");
    }

    connectedCallback() {

        if (!this.textarea) {
            return;
        }

        // Submit form on enter-key press (providing shift isn't being pressed)
        this.textarea.addEventListener('keypress', (evt) => {
            if (evt.key === 'Enter' && !evt.shiftKey && this.textarea) {
                evt.preventDefault();
                if (this.textarea.value.trim()) {
                    this.closest('form')?.requestSubmit();
                }
            }
        });

        // expand textarea as user adds lines
        this.textarea.addEventListener('input', () => {
            this.#adjustHeight();
        });

    }

    #adjustHeight = () => {
        if (!this.textarea) {
            return;
        }
        this.textarea.style.height = 'auto';
        this.textarea.style.height = `${this.textarea.scrollHeight}px`;
    };

    /**
     * Returns the current message
     * @returns string
     */
    getValue = () => {
        return this.querySelector("textarea")?.value.trim() || "";
    }

    /**
     * Clears the message and resets to starting height
     */
    reset = () => {
        if (!this.textarea) {
            return;
        }
        this.textarea.value = "";
        this.#adjustHeight();
    }
  
}
customElements.define('message-input', MessageInput);