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
      
      // Prevent message sending an empty message
      if (!messageInput || !userText) {
        return;
      }

      // Prevent message sending if there are files waiting to be processed
      if (document.querySelectorAll('file-status [data-status]:not([data-status="complete"])').length > 0) {
        this.#showError("<p>You have files waiting to be processed. Please wait for these to complete and then send the message again.</p>");
        return;
      }

      // Prevent message sending if uploaded files are over the max token size
      const maxTokens = parseInt(this.dataset.maxTokens || "0");
      let tokenCount = 0;
      let fileList = "";
      /** @type {NodeListOf<HTMLElement>} */
      let tokenElements = document.querySelectorAll('[data-tokens]');
      tokenElements.forEach((element) => {
        tokenCount += parseInt(element.dataset.tokens || "0");
        fileList += `<li><span>${element.dataset.name}: </span><span>${element.dataset.tokens} tokens</span></li>`;
      });
      if (tokenCount > maxTokens) {
        this.#showError(`
          ${tokenElements.length > 1 ? 
            `<p>The attached files are too large. Please remove some files and try again.</p>` :
            `<p>The attached file is too large. Please remove this and try again with a smaller file.</p>`
          }
          <p>The maximum size for this chat is ${maxTokens} tokens.</p>
          <p>Current file sizes:</p>
          <ul class="rb-token-sizes">${fileList}</ul>
        `);
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
      const fileName = /** @type{CustomEvent} */ (evt).detail.name;
      this.#showError(`<p><strong>${fileName}</strong> can't be uploaded</p><p>You can:</p><ul><li>try uploading again</li><li>check the document opens outside Redbox on your computer</li><li>report to <a href="mailto:redbox-copilot@cabinetoffice.gov.uk">Redbox support</a></li></ul>`);
    });

  }


  /**
   * @param {String} message
   */
  #showError(message) {
    let errorMessage = /** @type {import("./chat-message").ChatMessage} */ (
      document.createElement("chat-message")
    );
    errorMessage.dataset.role = "ai";
    this.messageContainer?.append(errorMessage);
    errorMessage.showError(message);
  }

}
customElements.define("chat-controller", ChatController);
