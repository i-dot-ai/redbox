// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class ChatMessageFooter extends RedboxElement {

  static properties = {
    id: { type: String, attribute: "data-id" },
    startText: { type: String, attribute: "data-start-text" }
  };

  constructor() {
    super();
    this.startText = this.startText || "";
  }

  render() {
    return html`
      <p class="rb-chat-message-footer__text">Redbox can get it wrong, you must check the accuracy of information before using</p>
      <div class="rb-chat-message-footer__actions-container">
        <fieldset>
          <legend class="govuk-visually-hidden">Response beginning: ${this.startText}</legend>
          <copy-text></copy-text>
        </fieldset>
        <feedback-buttons data-id=${this.id} data-start-text=${this.startText}></feedback-buttons>
      </div>
    `;
  }

}
customElements.define("chat-message-footer", ChatMessageFooter);
