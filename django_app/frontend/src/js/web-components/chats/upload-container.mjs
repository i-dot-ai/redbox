// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class UploadContainer extends RedboxElement {
  static properties = {
    docs: { type: Array, attribute: "data-docs" },
  };

  connectedCallback() {
    super.connectedCallback();
    // on message-send move the uploaded docs to the correct container
    document.addEventListener("chat-response-start", () => {
      const documentContainers = document.querySelectorAll("document-container");
      const lastDocumentContainer = documentContainers[documentContainers.length - 1];
      lastDocumentContainer.addDocuments(this.docs);
      this.docs = [];
    });
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
                <button @click=${this.#remove}>Remove</button>
              </li>
            `
          )}
        </ul>
      </div>
    `;
  }

  async addDocument(doc) {
  
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
        "X-CSRFToken": this.dataset.csrftoken,
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

  #remove = (evt) => {
    const item = evt.target.parentNode;
    const id = item.querySelector("file-status").dataset.id;
    
    // remove from UI
    item.remove();

    // remove from server
    const formData = new FormData();
    formData.append('doc_id', id);
    fetch(`/remove-doc/${id}`, {
      method: "POST",
      headers: {
        "X-CSRFToken": this.dataset.csrftoken,
      },
      body: formData,
    });
  }

}
customElements.define("upload-container", UploadContainer);
