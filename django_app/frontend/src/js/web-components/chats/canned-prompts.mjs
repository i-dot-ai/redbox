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
      <fieldset class="chat-options__options">
        <legend class="govuk-visually-hidden">Question suggestions</legend>
        <button @click=${this.#prepopulateMessageBox} class="chat-options__option chat-options__option_agenda" type="button">
            <img src="/static/icons/icon_square_doc.svg" alt=""/>
            <span class="govuk-visually-hidden">Populate question field with: </span>
            <span class="chat-options__prompt-text">Summarise this document</span>
        </button>
        <button @click=${this.#prepopulateMessageBox} class="chat-options__option chat-options__option_objectives" type="button">
            <img src="/static/icons/archery.svg" alt=""/>
            <span class="govuk-visually-hidden">Populate question field with: </span>
            <span class="chat-options__prompt-text">Draft an email about…</span>
        </button>
        <button @click=${this.#prepopulateMessageBox} class="chat-options__option chat-options__option_ps_role" type="button">
            <img src="/static/icons/person.svg" alt=""/>
            <span class="govuk-visually-hidden">Populate question field with: </span>
            <span class="chat-options__prompt-text">Reformat this to assist with neurodivergent communication…</span>
        </button>
      </fieldset>
      <p class="chat-options__info-text">Or type any question below</p>
    `;
  }

  #prepopulateMessageBox = (evt) => {
    const prompt = (evt.target.closest("button").querySelector(".chat-options__prompt-text").textContent?.trim() || "").replace("…", " ");
    /** @type HTMLInputElement | null */
    let chatInput = document.querySelector(".rb-chat-input textarea");
    if (chatInput) {
      chatInput.value = prompt;
      chatInput.focus();
      chatInput.selectionStart = chatInput.value.length;
    }

    // Send data to Plausible
    let plausible = /** @type {any} */ (window).plausible;
    if (typeof plausible !== "undefined") {
      plausible("Canned prompt", { props: { text: prompt } });
    }
  };

}
customElements.define("canned-prompts", CannedPrompts);
