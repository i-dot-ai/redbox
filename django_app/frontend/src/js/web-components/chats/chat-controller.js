// @ts-check

class ChatController extends HTMLElement {
  connectedCallback() {
    const messageForm = document.querySelector("#message-form"); // TO DO: Tidy this up
    this.messageContainer = this.querySelector(".js-message-container");
    const insertPosition = this.querySelector(".js-response-feedback");
    const feedbackButtons = /** @type {HTMLElement | null} */ (
      this.querySelector("feedback-buttons")
    );

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
      this.messageContainer?.insertBefore(userMessage, insertPosition);

      let documentContainer = document.createElement("document-container");
      this.messageContainer?.insertBefore(documentContainer, insertPosition);

      let aiMessage = /** @type {import("./chat-message").ChatMessage} */ (
        document.createElement("chat-message")
      );
      aiMessage.setAttribute("data-role", "ai");
      this.messageContainer?.insertBefore(aiMessage, insertPosition);

      const llm =
        /** @type {HTMLInputElement | null}*/ (
          document.querySelector("#llm-selector")
        )?.value || "";

      aiMessage.stream(
        userText,
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
      // (though we no longer have routes, it might be worth keeping for a little while, to see if users are still trying to use them)
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

    document.addEventListener("file-error", (evt) => {
      this.#showFileError(/** @type{CustomEvent} */ (evt).detail.name);
    });

  }


  /**
   * @param {String} fileName 
   */
  #showFileError (fileName) {
    let errorMessage = /** @type {import("./chat-message").ChatMessage} */ (
      document.createElement("chat-message")
    );
    errorMessage.dataset.role = "ai";
    this.messageContainer?.append(errorMessage);
    errorMessage.showError(`<p><strong>${fileName}</strong> can't be uploaded</p><p>You can:</p><ul><li>try uploading again</li><li>check the document opens outside Redbox on your computer</li><li>report to <a href="mailto:redbox-copilot@cabinetoffice.gov.uk">Redbox support</a></li></ul>`);
  };

}
customElements.define("chat-controller", ChatController);
