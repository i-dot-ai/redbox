// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class AttachDocument extends RedboxElement {

  render() {
    return html`
      <button class="rb-chat-input__button iai-icon-button rb-send-button" @click=${this.#attachDocument} type="button">
        <svg width="28" height="28" viewBox="32 16 29 29" fill="none" focusable="false" aria-hidden="true"><g filter="url(#A)"><use xlink:href="#C" fill="#edeef2"/></g><g filter="url(#B)"><use xlink:href="#C" fill="#fff"/></g><path d="M47.331 36.205v-8.438l3.89 3.89.972-1.007-5.556-5.556-5.556 5.556.972.972 3.889-3.854v8.438h1.389z" fill="currentColor"/><defs><filter x="17" y="1" width="65" height="65" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB"><feFlood flood-opacity="0" result="A"/><feColorMatrix in="SourceAlpha" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"/><feOffset dx="3" dy="3"/><feGaussianBlur stdDeviation="10"/><feColorMatrix values="0 0 0 0 0.141176 0 0 0 0 0.254902 0 0 0 0 0.364706 0 0 0 0.302 0"/><feBlend in2="A"/><feBlend in="SourceGraphic"/></filter><filter x="0" y="-16" width="85" height="85" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB"><feFlood flood-opacity="0" result="A"/><feColorMatrix in="SourceAlpha" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"/><feOffset dx="-4" dy="-4"/><feGaussianBlur stdDeviation="15"/><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 1 0"/><feBlend in2="A"/><feBlend in="SourceGraphic"/></filter><path d="M59 30.5C59 23.596 53.404 18 46.5 18S34 23.596 34 30.5 39.596 43 46.5 43 59 37.404 59 30.5z"/></defs></svg>
        Add file
      </button>
    `;
  }

  #attachDocument = () => {
    const uploadInitEvent = new CustomEvent("upload-init");
    document.dispatchEvent(uploadInitEvent);
  };

}
customElements.define("attach-document", AttachDocument);
