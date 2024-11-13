// @ts-check

class SendMessage extends HTMLElement {
  connectedCallback() {
    const stopButtonHtml = `
      <button class="iai-chat-input__button iai-icon-button rb-send-button" type="button">
        <div class="rb-square-icon"></div>
        Stop
      </button>
    `;
    this.innerHTML += stopButtonHtml;

    this.buttonSend = /** @type {HTMLButtonElement} */ (
      this.querySelector("button:nth-child(1)")
    );
    this.buttonStop = /** @type {HTMLButtonElement} */ (
      this.querySelector("button:nth-child(2)")
    );

    this.buttonStop.style.display = "none";
    this.buttonStop.addEventListener("click", () => {
      const stopStreamingEvent = new CustomEvent("stop-streaming");
      document.dispatchEvent(stopStreamingEvent);
    });

    document.addEventListener("chat-response-start", () => {
      if (!this.buttonSend || !this.buttonStop) {
        return;
      }
      this.buttonSend.style.display = "none";
      this.buttonStop.style.display = "flex";
    });

    document.addEventListener("chat-response-end", this.#showSendButton);
    document.addEventListener("stop-streaming", this.#showSendButton);
  }

  #showSendButton = () => {
    if (!this.buttonSend || !this.buttonStop) {
      return;
    }
    this.buttonSend.style.display = "flex";
    this.buttonStop.style.display = "none";
  };
}
customElements.define("send-message", SendMessage);
