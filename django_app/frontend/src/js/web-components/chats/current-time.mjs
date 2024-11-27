// @ts-check
import { LitElement, html } from "lit";

export class CurrentTime extends LitElement {
  static properties = {
    time: { type: String },
  };

  createRenderRoot() {
    return this;
  }

  constructor() {
    super();
    this.time = Date.now();
  }

  connectedCallback() {
    window.setInterval(() => {
      this.time = Date.now();
    }, 1000);
  }

  render() {
    return html`
      <p>${this.time}</p>
    `;
  }

}
customElements.define("current-time", CurrentTime);
