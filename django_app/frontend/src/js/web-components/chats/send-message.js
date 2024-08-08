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

    let buttonSend = /** @type {HTMLButtonElement} */ (
      this.querySelector("button:nth-child(1)")
    );
    let buttonStop = /** @type {HTMLButtonElement} */ (
      this.querySelector("button:nth-child(2)")
    );

    buttonStop.style.display = "none";
    buttonStop.addEventListener("click", () => {
      const stopStreamingEvent = new CustomEvent("stop-streaming");
      document.dispatchEvent(stopStreamingEvent);
    });

    document.addEventListener("chat-response-start", () => {
      buttonSend.style.display = "none";
      buttonStop.style.display = "flex";
    });
    const showSendButton = () => {
      buttonSend.style.display = "flex";
      buttonStop.style.display = "none";
    };
    document.addEventListener("chat-response-end", showSendButton);
    document.addEventListener("stop-streaming", showSendButton);
  }
}
customElements.define("send-message", SendMessage);
