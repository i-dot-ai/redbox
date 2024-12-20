// @ts-check

class FileStatus extends HTMLElement {

  static observedAttributes = ["data-id"];
  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "data-id" && oldValue !== newValue) {
      this.#checkStatus();
    }
  }

  connectedCallback() {
    this.#checkStatus();
  }

  async #checkStatus () {

    // UPDATE THESE AS REQUIRED
    const FILE_STATUS_ENDPOINT = "/file-status";
    const CHECK_INTERVAL_MS = 6000;

    if (this.textContent?.toLowerCase() === "complete" || !this.dataset.id) {
      return;
    }

    const response = await fetch(
      `${FILE_STATUS_ENDPOINT}?id=${this.dataset.id}`
    );
    const responseObj = await response.json();
    this.textContent = responseObj.status;
    this.dataset.status = responseObj.status.toLowerCase();

    if (responseObj.status.toLowerCase() === "complete") {
      const evt = new CustomEvent("doc-complete", {
        detail: this,
      });
      document.body.dispatchEvent(evt);
    } else {
      window.setTimeout(() => {
        this.#checkStatus();
      }, CHECK_INTERVAL_MS);
    }

  };

}
customElements.define("file-status", FileStatus);
