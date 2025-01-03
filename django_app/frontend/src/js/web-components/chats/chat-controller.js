// @ts-check

class ChatController extends HTMLElement {
  connectedCallback() {
    const messageForm = document.querySelector("#message-form"); // TO DO: Tidy this up
    const messageContainer = this.querySelector(".js-message-container");
    const insertPosition = this.querySelector(".js-response-feedback");
    const feedbackButtons = /** @type {HTMLElement | null} */ (
      this.querySelector("feedback-buttons")
    );
    let selectedDocuments = [];

    messageForm?.addEventListener("submit", (evt) => {
      evt.preventDefault();
      const messageInput =
        /** @type {import("./message-input").MessageInput} */ (
          document.querySelector("message-input")
        );
      const userText = messageInput?.getValue();
      if (!messageInput || !userText) {
        return;
      }

      let userMessage = /** @type {import("./chat-message").ChatMessage} */ (
        document.createElement("chat-message")
      );
      userMessage.setAttribute("data-text", userText);
      userMessage.setAttribute("data-role", "user");
      messageContainer?.insertBefore(userMessage, insertPosition);

      let aiMessage = /** @type {import("./chat-message").ChatMessage} */ (
        document.createElement("chat-message")
      );
      aiMessage.setAttribute("data-role", "ai");
      messageContainer?.insertBefore(aiMessage, insertPosition);

      const llm =
        /** @type {HTMLInputElement | null}*/ (
          document.querySelector("#llm-selector")
        )?.value || "";

      aiMessage.stream(
        userText,
        selectedDocuments.map(doc => doc.id),
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
      messageInput.reset();

      // if a route has been intentionally specified by a user, send an event to Plausible
      (() => {
        let plausible = /** @type {any} */ (window).plausible;
        if (typeof plausible === "undefined") {
          return;
        }
        if (userText.includes("@chat")) {
          plausible("User-specified-route", { props: { route: "@chat" } });
        }
        if (userText.includes("@chat/documents")) {
          plausible("User-specified-route", {
            props: { route: "@chat/documents" },
          });
        }
      })();
    });

    document.body.addEventListener("selected-docs-change", (evt) => {
      selectedDocuments = /** @type{CustomEvent} */ (evt).detail;
    });
  }
}
customElements.define("chat-controller", ChatController);
