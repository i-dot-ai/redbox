// @ts-check
import { html } from "lit";
import { RedboxElement } from "./redbox-element.mjs";

export class AnimatedLogo extends RedboxElement {

  static properties = {
    stopped: { type: Boolean, state: true },
  };

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", (evt) => {
      if (evt.key === "Escape") {
        this.stopped = true;
      }
    });
  }

  render() {
    return html`
      <img class=${this.stopped || !this.jsInitialised ? 'rb-icon' : 'rb-icon rb-icon--animated'} src="/static/icons/Icon_Redbox_200.svg" alt=""/>
    `;
  }

}
customElements.define("animated-logo", AnimatedLogo);
