// @ts-check
import { LitElement, html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class DocumentContainer extends RedboxElement {
  static properties = {
    docs: { type: Array, attribute: "data-docs" },
  };

  async addDocument(doc, csrfToken) {
  
    const tempId = crypto.randomUUID();

    this.docs.push({
      temp_id: tempId,
      file_name: doc.name,
      status: "Uploading"
    });
    this.requestUpdate();

    const formData = new FormData();
    formData.append('file', doc);
    formData.append('chat_id', this.dataset.chatid);

    const response = await fetch("/api/v0/file/", {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
      },
      body: formData,
    });
    if (!response.ok) {
      // TO DO: Handle error
    }

    const data = await response.json();
    this.docs.find(doc => doc.temp_id === tempId).id = data.file_id;
    this.requestUpdate();

  }

  render() {
    return html`
      <div class="rb-uploaded-docs">
        <h3>Uploaded documents</h3>
        <ul>
          ${this.docs.map(
            (doc) => html`
              <li>
                ${doc.file_name} : 
                <file-status data-id=${doc.id}>${doc.file_status}</file-status>
              </li>
            `
          )}
        </ul>
      </div>
    `;
  }
}
customElements.define("document-container", DocumentContainer);
