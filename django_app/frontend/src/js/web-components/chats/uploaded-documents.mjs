// @ts-check
import { LitElement, html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class UploadedDocuments extends RedboxElement {
  static properties = {
    docs: { type: Array, attribute: "data-docs" },
  };

  async addDocument(doc, csrfToken) {
    
    this.docs.push({
      file_name: doc.name
    });
    this.requestUpdate();

    const formData = new FormData();
    formData.append('uploadDocs', doc);

    const response = await fetch(`/upload/${this.dataset.chatid}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
      },
      body: formData,
    });
    if (!response.ok) {
      // TO DO: Handle error
    }
  }

  render() {
    return html`
      <div class="rb-uploaded-docs">
        <h3>Uploaded documents</h3>
        <ul>
          ${this.docs.map(
            (doc) => html`
              <li>${doc.file_name}</li>
            `
          )}
        </ul>
      </div>
    `;
  }
}
customElements.define("uploaded-documents", UploadedDocuments);
