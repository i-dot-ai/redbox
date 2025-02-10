// @ts-check
import { html } from "lit";
import { RedboxElement } from "./redbox-element.mjs";

class LoadingMessage extends RedboxElement {

  static properties = {
    ariaLabel: { type: String, attribute: "data-aria-label" },
    message: { type: String, attribute: "data-message" },
  };

  connectedCallback() {
    super.connectedCallback();
    this.message = this.message || "";
  }
  
  render() {
    return html`
      <div class="rb-loading-ellipsis govuk-body-s" aria-live="assertive" aria-label="${
        this.ariaLabel || this.message || "Loading"
      }">
        ${this.message || "Loading"}
        <span aria-hidden="true">.</span>
        <span aria-hidden="true">.</span>
        <span aria-hidden="true">.</span>
      </div>
    `;
  }

}
customElements.define("loading-message", LoadingMessage);
