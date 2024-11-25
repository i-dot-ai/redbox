// @ts-check

class CannedPrompts extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <h3 class="chat-options__heading govuk-heading-m">What would you like to ask your Redbox?</h3>
      <div class="chat-options__options">
          <button class="chat-options__option chat-options__option_agenda plausible-event-name--canned+prompt+draft+meeting+agenda" type="button">
              <img src="/static/icons/icon_square_doc.svg" alt=""/>
              Draft an agenda for a team meeting
          </button>
          <button class="chat-options__option chat-options__option_objectives plausible-event-name--canned+prompt+set+work+objectives" type="button">
              <img src="/static/icons/archery.svg" alt=""/>
              Help me set my work objectives
          </button>
          <button class="chat-options__option chat-options__option_ps_role plausible-event-name--canned+prompt+describe+role+permanent+secretary" type="button">
              <img src="/static/icons/person.svg" alt=""/>
              Describe the role of a Permanent Secretary
          </button>
      </div>
      <p class="chat-options__info-text">Or type any question below</p>
    `;

    let buttons = this.querySelectorAll("button");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        this.#prepopulateMessageBox(button.textContent?.trim() || "");
      });
    });

    window.setTimeout(() => {
      this.scrollIntoView({ block: "end" });
    }, 100);
  }

  /**
   * @param {string} prompt
   */
  #prepopulateMessageBox = (prompt) => {
    /** @type HTMLInputElement | null */
    let chatInput = document.querySelector(".iai-chat-input__input");
    if (chatInput) {
      chatInput.value = prompt;
      chatInput.focus();
      chatInput.selectionStart = chatInput.value.length;
    }
  };
}
customElements.define("canned-prompts", CannedPrompts);
