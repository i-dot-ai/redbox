// @ts-check

class FeedbackButtons extends HTMLElement {

    connectedCallback() {

        const html = `
            <button data-response="down">bad</button>
            <button data-response="up">good</button>
        `;
        this.innerHTML = /** @type {any} */ (DOMPurify.sanitize(html, {RETURN_TRUSTED_TYPE: true}));

        let buttons = this.querySelectorAll('button');
        buttons.forEach((button) => {
            button.addEventListener('click', () => {
                const response = button.dataset.response;
                if (response === this.dataset.status) {
                    this.dataset.status = '';
                } else {
                    this.dataset.status = response;
                }
            });
        });

    }
  
}
customElements.define('feedback-buttons', FeedbackButtons);
