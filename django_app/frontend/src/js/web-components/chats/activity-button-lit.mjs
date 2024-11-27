// @ts-check
import { LitElement, html } from "lit";

export class ActivityButton extends LitElement {
  static properties = {
    expanded: { type: Boolean, reflect: true },
  };

  createRenderRoot() {
    this.innerHTML = ""; // clear the SSR content
    return this;
  }

  constructor() {
    super();
    this.expanded = false;
  }

  render() {
    return html`
      <button @click=${this.#buttonClick} type="button">
        ${this.expanded ? `- Hide all activity` : `+ Show all activity`}
      </button>
    `;
  }

  #buttonClick = () => {
    this.expanded = !this.expanded;
  };
}
customElements.define("activity-button", ActivityButton);
