// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class DocumentContainer extends RedboxElement {
  static properties = {
    docs: { type: Array, attribute: "data-docs" },
  };

  async addDocuments(docs) {
    this.docs = docs;
    this.requestUpdate();
  }

  render() {
    return html`
      <div class="rb-uploaded-docs">
        <ul>
          ${this.docs?.map(
            (doc) => html`
              <li class="rb-uploaded-docs__item iai-chat-bubble" data-tokens=${doc.tokens} data-name=${doc.file_name}>
                <img src="/static/icons/doc.svg" alt="" loading="lazy"/>
                ${doc.file_name}
              </li>
            `
          )}
        </ul>
      </div>
    `;
  }
}
customElements.define("document-container", DocumentContainer);
