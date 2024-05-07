// @ts-check

let plausible = /** @type {any} */ (window).plausible;


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
                // send feedback to Plausible
                if (this.dataset.status && typeof(plausible) !== 'undefined') {
                    plausible(`Feedback-button-thumbs-${this.dataset.status}`);
                }
            });
        });

    }
  
}
customElements.define('feedback-buttons', FeedbackButtons);
