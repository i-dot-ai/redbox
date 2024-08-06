// @ts-check

class LoadingMessage extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="rb-loading-ellipsis govuk-body-s" aria-label="${
        this.dataset.dataAriaLabel || this.dataset.message || "Loading"
      }">
        ${this.dataset.message || "Loading"}
        <span aria-hidden="true">.</span>
        <span aria-hidden="true">.</span>
        <span aria-hidden="true">.</span>
      </div>
    `;
  }
}
customElements.define("loading-message", LoadingMessage);
