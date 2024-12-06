// @ts-check
import { LitElement, html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class ActivityButton extends RedboxElement {
  static properties = {
    expanded: { type: Boolean, reflect: true },
  };

  constructor() {
    super();
    this.expanded = false;
  }

  render() {
    return html` <button @click=${this.#buttonClick} type="button">${this.expanded ? `- Hide all activity` : `+ Show all activity`}</button> `;
  }

  #buttonClick = () => {
    this.expanded = !this.expanded;
  };
}
customElements.define("activity-button", ActivityButton);
