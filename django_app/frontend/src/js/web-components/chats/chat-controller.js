// @ts-check

class ChatController extends HTMLElement {
  connectedCallback() {
    const messageForm = this.closest("form");
    const messageContainer = this.querySelector(".js-message-container");
    const insertPosition = this.querySelector(".js-response-feedback");
    const feedbackButtons = /** @type {HTMLElement | null} */ (
      this.querySelector("feedback-buttons")
    );
    let selectedDocuments = [];

    messageForm?.addEventListener("submit", (evt) => {
      evt.preventDefault();
      const textArea = /** @type {HTMLInputElement | null} */ (
        document.querySelector(".js-user-text")
      );
      const userText = textArea?.value.trim();
      if (!textArea || !userText) {
        return;
      }

      let userMessage = document.createElement("chat-message");
      userMessage.setAttribute("data-text", userText);
      userMessage.setAttribute("data-role", "user");
      messageContainer?.insertBefore(userMessage, insertPosition);

      let aiMessage = /** @type {ChatMessage} */ (
        document.createElement("chat-message")
      );
      aiMessage.setAttribute("data-role", "ai");
      messageContainer?.insertBefore(aiMessage, insertPosition);

      const llm = /** @type {HTMLInputElement | null}*/ (
        document.querySelector("#llm-selector")
      )?.value;

      aiMessage.stream(
        userText,
        selectedDocuments,
        llm,
        this.dataset.sessionId,
        this.dataset.streamUrl || "",
        this
      );
      /** @type {HTMLElement | null} */ (
        aiMessage.querySelector(".iai-chat-bubble")
      )?.focus();

      // reset UI
      if (feedbackButtons) {
        feedbackButtons.dataset.status = "";
      }
      textArea.value = "";
    });

    document.body.addEventListener("selected-docs-change", (evt) => {
      selectedDocuments = /** @type{CustomEvent} */ (evt).detail;
    });
  }
}
customElements.define("chat-controller", ChatController);
