// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class DocumentUpload extends RedboxElement {
  static properties = {
    csrfToken: { type: String, attribute: "data-csrftoken" },
    chatId: { type: String, attribute: "data-chatid" },
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

      // send event to plausible analytics
      let plausible = /** @type {any} */ (window).plausible;
      if (typeof plausible !== "undefined") {
        plausible("drag-drop");
      }

    });

    // this needs throttling, otherwise it will flicker
    document.body.addEventListener("dragleave", (evt) => {
      this.dragDropTimer = window.setTimeout(() => {
        this.dragDropInProgress = false;
      }, 1);
    });

    // detect when the user clicks the "attach document" button
    document.addEventListener("upload-init", (evt) => {
      this.querySelector("input[type=file]").click();
    });

  }

  /**
   * @param {SubmitEvent} [evt]
   */
  #sendFiles = (evt) => {

    evt?.preventDefault();

    const uploadContainer = document.querySelector("upload-container");

    for (const doc of /** @type {HTMLFormElement} */(this.querySelector("input[type=file]")).files) {
      uploadContainer.addDocument(doc);
    }

    this.querySelector("input[type=file]").value = "";

  };

  render() {
    return html`
      <form class="rb-document-upload ${this.jsInitialised ? `govuk-visually-hidden` : ''}" action="/upload/" method="post" enctype="multipart/form-data">
        <input type="hidden" name="csrfmiddlewaretoken" value=${this["csrfToken"]} />
        <input type="hidden" name="chat_id" value=${this["chatId"]} />
        <label class="govuk-label" for="upload-docs">
          <h3 class="govuk-heading-s">Add a document</h3>
        </label>
        <input class="govuk-file-upload" @change=${this.#sendFiles} multiple id="upload-docs" name="uploadDocs" type="file" />
        <button class="govuk-!-display-inline-block" type="submit">Upload</button>
      </form>
      ${this.dragDropInProgress ? html`<p class="rb-uploaded-docs__drag-drop-message">Drop files here to upload to chat</p>` : ""}
    `;
  }
}
customElements.define("document-upload", DocumentUpload);
