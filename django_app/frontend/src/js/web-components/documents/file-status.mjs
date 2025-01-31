// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";


class FileStatus extends RedboxElement {

  constructor() {
    super();
    this.name = "";
  }

  static properties = {
    id: { type: String, attribute: "data-id" },
    status: { type: String, state: true },
    positionInQueue: { type: Number, state: true },
    name: { type: String, attribute: "data-name" },
    tokens: { type: Number, state: true }
  };

  connectedCallback() {
    super.connectedCallback();
    this.status = this.textContent || "Uploading";
    this.tokens = 0;
    this.#checkStatus();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.status = "Error"; // to prevent additional requests
  }

  render() {
    let statusText = this.status;
    let statusAttr = this.status?.toLowerCase();
    if (this.status === "Processing" && this.positionInQueue > 0) {
      statusText = `${this.positionInQueue} ahead in queue`;
      statusAttr = "queued";
    }

    let icon;
    if (statusAttr === "complete") {
      icon = html`<img src="/static/icons/file-status/tick.svg" alt="" width="23" height="20"/>`;
    } else if (statusAttr === "queued") {
        icon = html`<img src="/static/icons/file-status/queueing.svg" alt="" width="23" height="20"/>`;
    } else if (statusAttr === "processing") {
        icon = html`<img src="/static/icons/file-status/processing.svg" alt="" width="22" height="20"/>`;
    } else if (statusAttr === "error") {
      icon = html`<img src="/static/icons/file-status/exclamation.svg" alt="" width="23" height="20"/>`;
    } else if (statusAttr === "uploading") {
      icon = html`<img src="/static/icons/file-status/uploading.svg" alt="" width="23" height="20"/>`;
    }

    return html`
      ${icon}
      <span data-status=${statusAttr} data-tokens=${this.tokens} data-name=${this.name} aria-live="assertive" aria-atomic="true">
        ${statusText}
        <span class="govuk-visually-hidden">${this.name}</span>
      </span>
    `;
  }

  #sendErrorEvent() {
    const fileErrorEvent = new CustomEvent("file-error", {
      detail: {
        name: this.name
      },
    });
    document.dispatchEvent(fileErrorEvent);
  }

  async #checkStatus () {

    // UPDATE THESE AS REQUIRED
    const FILE_STATUS_ENDPOINT = "/file-status";
    const CHECK_INTERVAL_MS = 1000;

    if (this.dataset.error) {
      this.status = "Error";
      this.#sendErrorEvent();
      return;
    }

    if (!this.id) {
      window.setTimeout(() => {
        this.#checkStatus();
      }, CHECK_INTERVAL_MS);
      return;
    }

    if (this.status === "Complete" || this.status === "Error" || !this.id) {
      return;
    }

    const response = await fetch(
      `${FILE_STATUS_ENDPOINT}?id=${this.id}`
    );
    const responseObj = await response.json();
    this.status = responseObj.status;
    this.positionInQueue = responseObj.position_in_queue;
    this.tokens = responseObj.tokens || 0;

    if (responseObj.status.toLowerCase() === "error") {
      this.#sendErrorEvent();
      return;
    }

    if (responseObj.status === "Complete") {
      return;
    }

    window.setTimeout(() => {
      this.#checkStatus();
    }, CHECK_INTERVAL_MS);

  };

}
customElements.define("file-status", FileStatus);
