// @ts-check

class FileStatus extends HTMLElement {

  static observedAttributes = ["data-id"];
  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "data-id" && oldValue !== newValue) {
      this.#checkStatus();
    }
  }

  connectedCallback() {
    if (!this.textContent) {
      this.textContent = "Uploading";
    }
    this.#checkStatus();
  }

  disconnectedCallback() {
    this.dataset.id = "";
  }

  async #checkStatus () {

    // UPDATE THESE AS REQUIRED
    const FILE_STATUS_ENDPOINT = "/file-status";
    const CHECK_INTERVAL_MS = 2000;

    if (this.textContent?.toLowerCase() === "complete" || this.textContent?.toLowerCase() === "error" || !this.dataset.id) {
      return;
    }

    const response = await fetch(
      `${FILE_STATUS_ENDPOINT}?id=${this.dataset.id}`
    );
    const responseObj = await response.json();
    this.textContent = responseObj.status;
    this.dataset.status = responseObj.status.toLowerCase();

    if (responseObj.status.toLowerCase() === "error") {
      const fileErrorEvent = new CustomEvent("file-error", {
        detail: {
          name: this.dataset.name
        },
      });
      document.dispatchEvent(fileErrorEvent);
      return;
    }

    if (responseObj.status.toLowerCase() === "complete") {
      return;
    }

    window.setTimeout(() => {
      this.#checkStatus();
    }, CHECK_INTERVAL_MS);

  };

}
customElements.define("file-status", FileStatus);
