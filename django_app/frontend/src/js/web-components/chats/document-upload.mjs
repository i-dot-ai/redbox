// @ts-check
import { LitElement, html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class DocumentUpload extends RedboxElement {
  static properties = {
    csrfToken: { type: String, attribute: "data-csrf-token" },
    chatId: { type: String, attribute: "data-chat-id" },
    dragDropInProgress: { type: Boolean, state: true },
  };

  connectedCallback() {
    super.connectedCallback();

    document.body.addEventListener("dragover", (evt) => {
      evt.preventDefault();
      window.clearTimeout(this.dragDropTimer);
      this.dragDropInProgress = true;
    });

    document.body.addEventListener("drop", (evt) => {
      evt.preventDefault();
      this.dragDropInProgress = false;
      const files = evt.dataTransfer?.files;
      if (!files) {
        return;
      }
      // copy files to the file-input element
      const dataTransfer = new DataTransfer();
      for (let i = 0; i < files.length; i++) {
        dataTransfer.items.add(files[i]);
      }
      /** @type {HTMLInputElement} */ (this.querySelector("input[type=file]")).files = dataTransfer.files;
      this.#sendFiles();
    });

    // this needs throttling, otherwise it will flicker
    document.body.addEventListener("dragleave", (evt) => {
      this.dragDropTimer = window.setTimeout(() => {
        this.dragDropInProgress = false;
      }, 1);
    });
  }

  /**
   * @param {SubmitEvent} [evt]
   */
  #sendFiles = async (evt) => {
    evt?.preventDefault();
    const formData = new FormData(this.querySelector("form") || undefined);
    /*
    for (let [key, value] of formData.entries()) {
      console.log(key, value);
    }
    */
    const response = await fetch("/upload/", {
      method: "POST",
      headers: {
        "X-CSRFToken": this["csrfToken"],
      },
      body: formData,
    });
    if (!response.ok) {
      // TO DO: Handle error
    }
    // TO DO: add document icons to the chat
    /** @type {HTMLInputElement} */ (this.querySelector("input[type=file]")).value = "";
  };

  render() {
    return html`
      <form class="rb-document-upload" @submit=${this.#sendFiles} action="/upload/" method="post" enctype="multipart/form-data">
        <input type="hidden" name="csrfmiddlewaretoken" value=${this["csrfToken"]} />
        <input type="hidden" name="chat_id" value=${this["chatId"]} />
        <label class="govuk-label" for="upload-docs">
          <h3 class="govuk-heading-s">Add a document</h3>
        </label>
        <div id="upload-docs-notification">
          <p class="govuk-body-l">You can use up to, and including, Official Sensitive documents. Do not upload any documents with personal data.</p>
        </div>
        <p class="govuk-body rb-file-types" id="upload-docs-filetypes">Limit 200MB per file: EML, HTML, JSON, MD, MSG, RST, RTF, TXT, XML, CSV, DOC, DOCX, EPUB, ODT, PDF, PPT, PPTX, TSV, XLSX, HTM</p>
        <input class="govuk-file-upload" multiple id="upload-docs" name="uploadDocs" type="file" aria-describedby="upload-docs-notification upload-docs-filetypes" />
        <button class="govuk-!-display-inline-block" type="submit">Upload</button>
      </form>
      ${this.dragDropInProgress ? html`<p>Drop files here to upload to chat</p>` : ""}
    `;
  }
}
customElements.define("document-upload", DocumentUpload);
