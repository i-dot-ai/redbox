// @ts-check
import { LitElement, html } from "lit";


class BaseElement extends LitElement {
  // clear the SSR content and prevents Shadow DOM by default
  createRenderRoot() {
    this.innerHTML = "";
    return this;
  }
}


export class ActivityButton extends BaseElement {
  static properties = {
    expanded: { type: Boolean, reflect: true },
  };

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
