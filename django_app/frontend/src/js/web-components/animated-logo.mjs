// @ts-check
import { html } from "lit";
import { RedboxElement } from "./redbox-element.mjs";

export class AnimatedLogo extends RedboxElement {

  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("mouseenter", (evt) => {
      let img = this.querySelector("img");
      img?.classList.remove("rb-icon--animated");
      window.setTimeout(() => {
        img?.classList.add("rb-icon--animated");
      }, 1);
    });
  }

  render() {
    return html`
      <img class=${this.jsInitialised ? 'rb-icon rb-icon--animated' : 'rb-icon'} src="/static/icons/Icon_Redbox_200.svg" alt=""/>
    `;
  }

}
customElements.define("animated-logo", AnimatedLogo);
