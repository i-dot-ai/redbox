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
      const maxTokens = parseInt(/** @type {HTMLInputElement} */(document.querySelector("#max-tokens")).value || "0");
      let tokenCount = 0;
      let fileList = "";
      /** @type {NodeListOf<HTMLElement>} */
      let tokenElements = document.querySelectorAll('[data-tokens]');
      tokenElements.forEach((element) => {
        tokenCount += parseInt(element.dataset.tokens || "0");
        fileList += `<li><span>${element.dataset.name}: </span><span>${element.dataset.tokens} tokens</span></li>`;
      });
      if (tokenCount > maxTokens) {
        const models = JSON.parse(this.dataset.models || "[]");
        this.#showError(`
          <p>The attached file(s) are too large. The maximum size for this chat is ${maxTokens} tokens.</p>
          <p>You can try:</p>
          <ul>
            <li>Removing any files attached since the last message</li>
            <li>Reducing the size of the files attached</li>
            <li>Selecting a different model</li>
          </ul>
          <p>Current file sizes:</p>
          <ul class="rb-token-sizes">${fileList}</ul>
          <details>
            <summary>Model token limits</summary>
            <ul class="rb-token-sizes">
              ${models.map((model) => `<li><span>${model.name}: </span><span>${model.max_tokens} tokens</li>`).join("")}
            </ul>
          </details>
        `);
        (() => {
          let plausible = /** @type {any} */ (window).plausible;
          if (typeof plausible === "undefined") {
            return;
          }
          plausible("Token limit message shown");
        })();
        return;
      }

      let userMessage = /** @type {import("./chat-message").ChatMessage} */ (
        document.createElement("chat-message")
      );
      userMessage.setAttribute("data-text", userText);
      userMessage.setAttribute("data-role", "user");
      let userMessageListItem = document.createElement("li");
      userMessageListItem.appendChild(userMessage);
      this.messageContainer?.insertBefore(userMessageListItem, insertPosition);

      let documentContainer = document.createElement("document-container");
      let documentContainerListItem = document.createElement("li");
      documentContainerListItem.appendChild(documentContainer);
      this.messageContainer?.insertBefore(documentContainerListItem, insertPosition);

      let aiMessage = /** @type {import("./chat-message").ChatMessage} */ (
        document.createElement("chat-message")
      );
      aiMessage.setAttribute("data-role", "ai");
      let aiMessageListItem = document.createElement("li");
      aiMessageListItem.appendChild(aiMessage);
      this.messageContainer?.insertBefore(aiMessageListItem, insertPosition);

      const llm =
        /** @type {HTMLInputElement | null}*/ (
          document.querySelector("#llm-selector")
        )?.value || "";

      aiMessage.stream(
        userText,
        llm,
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
