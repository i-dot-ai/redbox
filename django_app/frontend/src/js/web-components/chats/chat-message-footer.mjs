// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class ChatMessageFooter extends RedboxElement {

  static properties = {
    id: { type: String, attribute: "data-id" }
  };

  render() {
    return html`
      <p class="rb-chat-message-footer__text">Redbox can get it wrong, you must check the accuracy of information before using</p>
      <div class="rb-chat-message-footer__actions-container">
        <copy-text></copy-text>
        <feedback-buttons data-id=${this.id}></feedback-buttons>
      </div>
    `;
  }

}
customElements.define("chat-message-footer", ChatMessageFooter);
