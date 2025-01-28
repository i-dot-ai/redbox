// @ts-check
import { html, nothing } from "lit";
import { RedboxElement } from "../redbox-element.mjs";


class CannedPrompts extends RedboxElement {
  
  connectedCallback() {
    super.connectedCallback();
    window.setTimeout(() => {
      this.scrollIntoView({ block: "end" });
    }, 100);
  }

  render() {
    return html`
      <h3 class="chat-options__heading govuk-heading-m">
        <animated-logo class="chat-options__icon"></animated-logo>
        What would you like to ask?
      </h3>
      <div class="chat-options__options">
          <button @click=${this.#prepopulateMessageBox} class="chat-options__option chat-options__option_agenda plausible-event-name--canned+prompt+draft+meeting+agenda" type="button">
              <img src="/static/icons/icon_square_doc.svg" alt=""/>
              Summarise this document
          </button>
          <button @click=${this.#prepopulateMessageBox} class="chat-options__option chat-options__option_objectives plausible-event-name--canned+prompt+set+work+objectives" type="button">
              <img src="/static/icons/archery.svg" alt=""/>
              Draft an email about…
          </button>
          <button @click=${this.#prepopulateMessageBox} class="chat-options__option chat-options__option_ps_role plausible-event-name--canned+prompt+describe+role+permanent+secretary" type="button">
              <img src="/static/icons/person.svg" alt=""/>
              Reformat this to assist with neurodivergent communication…
          </button>
      </div>
      <p class="chat-options__info-text">Or type any question below</p>
    `;
  }

  #prepopulateMessageBox = (evt) => {
    const prompt = (evt.target.textContent?.trim() || "").replace("…", " ");
    /** @type HTMLInputElement | null */
    let chatInput = document.querySelector(".rb-chat-input textarea");
    if (chatInput) {
      chatInput.value = prompt;
      chatInput.focus();
      chatInput.selectionStart = chatInput.value.length;
    }
  };

}
customElements.define("canned-prompts", CannedPrompts);
