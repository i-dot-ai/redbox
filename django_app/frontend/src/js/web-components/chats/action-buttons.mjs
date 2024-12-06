// @ts-check
import { LitElement, html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class ActionButtons extends RedboxElement {
  static properties = {
    messageId: { type: String, attribute: 'data-id' },
    showRating: { type: Boolean, state: true },
  };

  constructor() {
    super();
    this.showRating = false;
  }

  render() {
    return html`
      <div class="rb-action-buttons">
        <button class="rb-action-buttons__button rb-action-buttons__button--copy" @click=${this.#copyToClipboard} type="button">
          <svg width="20" height="25" viewBox="0 0 20 25" fill="none" focusable="false" aria-hidden="true">
            <path d="M13 2.5H7C6.44772 2.5 6 2.94772 6 3.5V5.5C6 6.05228 6.44772 6.5 7 6.5H13C13.5523 6.5 14 6.05228 14 5.5V3.5C14 2.94772 13.5523 2.5 13 2.5Z" stroke="black" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M6 4.5H4C3.46957 4.5 2.96086 4.71071 2.58579 5.08579C2.21071 5.46086 2 5.96957 2 6.5V20.5C2 21.0304 2.21071 21.5391 2.58579 21.9142C2.96086 22.2893 3.46957 22.5 4 22.5H16C16.5304 22.5 17.0391 22.2893 17.4142 21.9142C17.7893 21.5391 18 21.0304 18 20.5V18.5" stroke="black" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M14 4.5H16C16.5304 4.5 17.0391 4.71071 17.4142 5.08579C17.7893 5.46086 18 5.96957 18 6.5V10.5" stroke="black" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M19 14.5H9" stroke="black" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M13 10.5L9 14.5L13 18.5" stroke="black" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>Copy</span>
        </button>
        <button class="rb-action-buttons__button rb-action-buttons__button--rate" @click=${this.#rateResponse} type="button" aria-expanded=${this.showRating} aria-controls="rating-${this.messageId}">
          <svg width="22" height="22" viewBox="0 0 25 25" fill="none" focusable="false" aria-hidden="true">
            <path d="M12.0172 1.68381C12.1639 1.21711 12.8244 1.21711 12.9711 1.68381L15.1648 8.66018C15.3613 9.28511 15.9406 9.71024 16.5957 9.71024H23.7624C24.2428 9.71024 24.4468 10.3217 24.0626 10.6101L18.2088 15.0049C17.7002 15.3867 17.4877 16.0477 17.6784 16.6544L19.901 23.7227C20.0468 24.1863 19.5124 24.5643 19.1238 24.2726L13.3947 19.9714C12.8612 19.5708 12.1271 19.5708 11.5936 19.9714L5.86446 24.2726C5.47585 24.5643 4.94152 24.1863 5.08728 23.7227L7.30983 16.6544C7.50059 16.0477 7.28806 15.3867 6.77949 15.0049L0.925668 10.6101C0.5415 10.3217 0.745481 9.71024 1.22586 9.71024H8.3926C9.0477 9.71024 9.62702 9.28511 9.82353 8.66017L12.0172 1.68381Z" fill="none" stroke="currentColor" />
          </svg>
          <span>Rate</span>
        </button>
      </div>
      ${this.showRating ? html` <feedback-buttons data-id=${this.messageId}></feedback-buttons> ` : ""}
    `;
  }

  #copyToClipboard = () => {
    const content = this.previousElementSibling?.querySelector(".iai-chat-bubble__text");
    if (!content) {
      return;
    }
    const listener = (evt) => {
      evt.clipboardData.setData("text/html", content.innerHTML);
      evt.clipboardData.setData("text/plain", content.textContent);
      evt.preventDefault();
    };
    document.addEventListener("copy", listener);
    document.execCommand("copy");
    document.removeEventListener("copy", listener);
    // TO DO: Give feedback to user
  };

  #rateResponse = () => {
    this.showRating = !this.showRating;
  };
}
customElements.define("action-buttons", ActionButtons);
