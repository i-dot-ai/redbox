// @ts-check

import "../loading-message.js";

export class ChatMessage extends HTMLElement {
  constructor() {
    super();
    this.programmaticScroll = false;
    this.plausibleRouteDataSent = false;
  }

  connectedCallback() {
    this.uuid = crypto.randomUUID();
    this.innerHTML = `
      <div class="iai-chat-bubble govuk-body {{ classes }}" data-role="${
        this.dataset.role
      }" tabindex="-1">
          <div class="iai-chat-bubble__header">
              <div class="iai-chat-bubble__role">${
                this.dataset.role === "ai" ? `<img src="/static/icons/Icon_Redbox_200.svg" alt=""/> Redbox` : "You"
              }</div>
          </div>
          <markdown-converter class="iai-chat-bubble__text" data-role="${this.dataset.role}"></markdown-converter>
          ${
            !this.dataset.text
              ? `
                <loading-message data-aria-label="Loading message"></loading-message>
                <div class="rb-loading-complete govuk-visually-hidden" aria-live="assertive"></div>
              `
              : ""
          }
          <div class="govuk-notification-banner govuk-notification-banner--error govuk-!-margin-bottom-3 govuk-!-margin-top-3" role="alert" aria-labelledby="notification-title-${this.uuid}" data-module="govuk-notification-banner" hidden>
              <div class="govuk-notification-banner__header">
                  <h3 class="govuk-notification-banner__title" id="notification-title-${this.uuid}">Error</h3>
              </div>
              <div class="govuk-notification-banner__content">
                  <p class="govuk-notification-banner__heading"></p>
              </div>
          </div>
      </div>
    `;

    // Add any existing markdown content - can't update directly to the above HTML string as user HTML may be removed
    /** @type {import("./markdown-converter").MarkdownConverter} */(this.querySelector("markdown-converter")).update(this.dataset.text || "");

    // ensure new chat-messages aren't hidden behind the chat-input
    this.programmaticScroll = true;
    this.scrollIntoView({ block: "end" });

    this.responseContainer =
      /** @type {import("./markdown-converter").MarkdownConverter} */ (
        this.querySelector("markdown-converter")
      );

    this.loadingMessage = /** @type HTMLElement */ (
      this.querySelector("loading-message")
    );

  }

  /**
   * Streams an LLM response
   * @param {string} message
   * @param {string} llm
   * @param {string | undefined} sessionId
   * @param {string} endPoint
   * @param {HTMLElement} chatControllerRef
   */
  stream = (
    message,
    llm,
    sessionId,
    endPoint,
    chatControllerRef
  ) => {
    // Scroll behaviour - depending on whether user has overridden this or not
    let scrollOverride = false;
    window.addEventListener("scroll", (evt) => {
      if (this.programmaticScroll) {
        this.programmaticScroll = false;
        return;
      }
      scrollOverride = true;
    });

    let responseComplete = this.querySelector(".rb-loading-complete");
    let webSocket = new WebSocket(endPoint);
    let streamedContent = "";

    // Stop streaming on escape-key or stop-button press
    const stopStreaming = () => {
      this.dataset.status = "stopped";
      webSocket.close();
    };
    this.addEventListener("keydown", (evt) => {
      if (evt.key === "Escape" && this.dataset.status === "streaming") {
        stopStreaming();
      }
    });
    document.addEventListener("stop-streaming", stopStreaming);

    webSocket.onopen = (event) => {
      webSocket.send(
        JSON.stringify({
          message: message,
          sessionId: sessionId,
          llm: llm,
        })
      );
      this.dataset.status = "streaming";
      const chatResponseStartEvent = new CustomEvent("chat-response-start");
      document.dispatchEvent(chatResponseStartEvent);
    };

    webSocket.onerror = (event) => {
      if (!this.responseContainer) {
        return;
      }
      this.responseContainer.innerHTML =
        "There was a problem. Please try sending this message again.";
      this.dataset.status = "error";
    };

    webSocket.onclose = (event) => {
      this.loadingMessage?.remove();
      if (responseComplete) {
        responseComplete.textContent = "Response complete";
      }
      if (this.dataset.status !== "stopped") {
        this.dataset.status = "complete";
      }
      const stopStreamingEvent = new CustomEvent("stop-streaming");
      document.dispatchEvent(stopStreamingEvent);
    };

    webSocket.onmessage = (event) => {
      let response;
      try {
        response = JSON.parse(event.data);
      } catch (err) {
        console.log("Error getting JSON response", err);
      }

      if (response.type === "text") {
        streamedContent += response.data;
        this.responseContainer?.update(streamedContent);
      } else if (response.type === "session-id") {
        chatControllerRef.dataset.sessionId = response.data;
      } else if (response.type === "end") {
        let chatMessageFooter = document.createElement("chat-message-footer");
        chatMessageFooter.dataset.id = this.uuid;
        this.parentElement?.appendChild(chatMessageFooter);

        const chatResponseEndEvent = new CustomEvent("chat-response-end", {
          detail: {
            title: response.data.title,
            session_id: response.data.session_id,
          },
        });
        document.dispatchEvent(chatResponseEndEvent);
      } else if (response.type === "error") {
        this.querySelector(".govuk-notification-banner")?.removeAttribute(
          "hidden"
        );
        let errorContentContainer = this.querySelector(
          ".govuk-notification-banner__heading"
        );
        if (errorContentContainer) {
          errorContentContainer.innerHTML = response.data;
        }
      }

      // ensure new content isn't hidden behind the chat-input
      // but stop scrolling if message is at the top of the screen
      if (!scrollOverride) {
        const TOP_POSITION = 88;
        const boxInfo = this.getBoundingClientRect();
        const newTopPosition =
          boxInfo.top -
          (boxInfo.height - (this.previousHeight || boxInfo.height));
        this.previousHeight = boxInfo.height;
        if (newTopPosition > TOP_POSITION) {
          this.programmaticScroll = true;
          this.scrollIntoView({ block: "end" });
        } else {
          scrollOverride = true;
          this.scrollIntoView();
          window.scrollBy(0, -TOP_POSITION);
        }
      }
    };
  };

  /** This is the same as adding content to the data-text attribute, except that this also reads the content out to screen-reader users */
  showError(message) {
    this.dataset.status = "stopped";
    this.loadingMessage?.remove();
    this.setAttribute("aria-live", "assertive");
    window.setTimeout(() => {
      if (this.responseContainer) {
        this.responseContainer.innerHTML = message;
      }
    }, 100);
  };

}
customElements.define("chat-message", ChatMessage);
