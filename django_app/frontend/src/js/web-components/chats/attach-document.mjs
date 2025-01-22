// @ts-check
import { html } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class AttachDocument extends RedboxElement {

  render() {
    return html`
      <button class="rb-chat-input__attach-button" @click=${this.#attachDocument} type="button">
        <svg width="38" height="20" viewBox="0 0 38 20" aria-hidden="true" focusable="false">
          <path d="M26.5972 1.40745C24.727 -0.468905 21.6955 -0.468905 19.8262 1.40745L10.2322 11.09C9.92141 11.4036 9.92279 11.9108 10.2352 12.2228C10.5477 12.5347 11.053 12.5333 11.3638 12.2197L20.9563 2.53871C22.2008 1.28947 24.222 1.28947 25.4689 2.5404C26.7155 3.79177 26.7155 5.82049 25.4689 7.07123L15.5931 17.0374C14.8155 17.8174 13.5521 17.8174 12.7728 17.0357C11.9938 16.2538 11.9938 14.9859 12.7731 14.2037L20.9548 5.99096C20.955 5.99069 20.9552 5.9904 20.9555 5.99013C21.2672 5.67815 21.7715 5.67838 22.0829 5.99088C22.3944 6.30365 22.3944 6.81058 22.0829 7.12335L18.1336 11.0884C17.822 11.4013 17.8221 11.9085 18.1337 12.2212C18.4454 12.534 18.9507 12.5339 19.2622 12.2211L23.2115 8.25611C24.1462 7.31777 24.1462 5.7965 23.2114 4.85812C22.2765 3.9197 20.761 3.9197 19.8262 4.85812C19.8256 4.85864 19.8252 4.85924 19.8247 4.85977L11.6446 13.071C10.2421 14.4787 10.2421 16.761 11.6446 18.1687C13.0472 19.5757 15.3204 19.5757 16.7228 18.169L26.5987 8.20268C28.4673 6.32794 28.4673 3.28466 26.5972 1.40745Z" fill="currentColor"/>
        </svg>
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
