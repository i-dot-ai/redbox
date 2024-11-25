// @ts-check

import "../loading-message.js";

/**
 * Send Plausible data on tool-tip hover
 * @param {Event} evt
 */
const sendTooltipViewEvent = (evt) => {
  let plausible = /** @type {any} */ (window).plausible;
  if (typeof plausible !== "undefined") {
    plausible("Route-tooltip-view");
  }
  // cancel event listener so events only get sent once
  let targetElement = /** @type{HTMLElement | null | undefined} */ (evt.target);
  if (targetElement?.nodeName !== "TOOL-TIP") {
    targetElement = targetElement?.closest("tool-tip");
  }
  targetElement?.removeEventListener("mouseover", sendTooltipViewEvent);
};
// Do this for any SSR tool-tips on the page
(() => {
  const tooltips = document.querySelectorAll("tool-tip");
  tooltips.forEach((tooltip) => {
    tooltip.addEventListener("mouseover", sendTooltipViewEvent);
  });
})();

export class ChatMessage extends HTMLElement {
  constructor() {
    super();
    this.programmaticScroll = false;
    this.plausibleRouteDataSent = false;
  }

  connectedCallback() {
    const uuid = crypto.randomUUID();
    this.innerHTML = `
      <div class="rb-activity">
        <activity-button class="rb-activity__btn"></activity-button>
      </div>
      <div class="iai-chat-bubble govuk-body {{ classes }}" data-role="${
        this.dataset.role
      }" tabindex="-1">
          <div class="iai-chat-bubble__header">
              <div class="iai-chat-bubble__role">${
                this.dataset.role === "ai" ? "Redbox" : "You"
              }</div>
          </div>
          <markdown-converter class="iai-chat-bubble__text">${
            this.dataset.text || ""
          }</markdown-converter>
          ${
            !this.dataset.text
              ? `
                <loading-message data-aria-label="Loading message"></loading-message>
                <div class="rb-loading-complete govuk-visually-hidden" aria-live="assertive"></div>
              `
              : ""
          }
          <sources-list data-id="${uuid}"></sources-list>
          <div class="govuk-notification-banner govuk-notification-banner--error govuk-!-margin-bottom-3 govuk-!-margin-top-3" role="alert" aria-labelledby="notification-title-${uuid}" data-module="govuk-notification-banner" hidden>
              <div class="govuk-notification-banner__header">
                  <h3 class="govuk-notification-banner__title" id="notification-title-${uuid}">Error</h3>
              </div>
              <div class="govuk-notification-banner__content">
                  <p class="govuk-notification-banner__heading"></p>
              </div>
          </div>
      </div>
  `;

    // Add feedback buttons
    if (this.dataset.role === "ai") {
      this.feedbackButtons = /** @type {import("./feedback-buttons").FeedbackButtons} */(document.createElement("feedback-buttons"));
  this.parentElement?.appendChild(this.feedbackButtons);
    }

    // ensure new chat-messages aren't hidden behind the chat-input
    this.programmaticScroll = true;
    this.scrollIntoView({ block: "end" });

    // Insert route_display HTML
    const routeTemplate = /** @type {HTMLTemplateElement} */ (
      document.querySelector("#template-route-display")
    );
    const routeClone = document.importNode(routeTemplate.content, true);

    this.querySelector(".iai-chat-bubble__header")?.appendChild(routeClone);
    this.querySelector("tool-tip")?.addEventListener(
      "mouseover",
      sendTooltipViewEvent
    );

  }

  #addFootnotes = (content) => {
    let footnotes = this.querySelectorAll("sources-list a[data-text]");
    footnotes.forEach((footnote, footnoteIndex) => {
      const matchingText = footnote.getAttribute("data-text");
      if (!matchingText || !this.responseContainer) {
        return;
      }
      /*
      this.responseContainer?.update(
        content.replace(matchingText, `${matchingText}<a href="#${footnote.id}" aria-label="Footnote ${footnoteIndex + 1}">[${footnoteIndex + 1}]</a>`)
      );
      */
      this.responseContainer.innerHTML =
        this.responseContainer.innerHTML.replace(
          matchingText,
          `${matchingText}<a class="rb-footnote-link" href="#${
            footnote.id
          }" aria-label="Footnote ${footnoteIndex + 1}">${
            footnoteIndex + 1
          }</a>`
        );
    });
  };

  /**
   * Displays an activity above the message
   * @param {string} message
   * @param { "ai" | "user"} type
   */
  addActivity = (message, type) => {
    let activityElement = document.createElement("p");
    activityElement.classList.add("rb-activity__item", `rb-activity__item--${type}`);
    activityElement.textContent = message;
    this.querySelector(".rb-activity")?.appendChild(activityElement);
  };

  /**
   * Streams an LLM response
   * @param {string} message
   * @param {string[]} selectedDocuments An array of IDs
   * @param {string[]} activities
   * @param {string} llm
   * @param {string | undefined} sessionId
   * @param {string} endPoint
   * @param {HTMLElement} chatControllerRef
   */
  stream = (
    message,
    selectedDocuments,
    activities,
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

    this.responseContainer =
      /** @type {import("../markdown-converter").MarkdownConverter} */ (
        this.querySelector("markdown-converter")
      );
    let sourcesContainer = /** @type {import("./sources-list").SourcesList} */ (
      this.querySelector("sources-list")
    );
    /** @type {import("./feedback-buttons").FeedbackButtons | null} */
    let responseLoading = /** @type HTMLElement */ (
      this.querySelector(".rb-loading-ellipsis")
    );
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
          selectedFiles: selectedDocuments,
          activities: activities,
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
      responseLoading.style.display = "none";
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
      } else if (response.type === "source") {
        sourcesContainer.add(
          response.data.file_name,
          response.data.url,
          response.data.text_in_answer
        );
      } else if (response.type === "route") {
        let route = this.querySelector(".iai-chat-bubble__route");
        let routeText = route?.querySelector(".iai-chat-bubble__route-text");
        if (route && routeText) {
          routeText.textContent = response.data;
          route.removeAttribute("hidden");
        }

        // send route to Plausible
        let plausible = /** @type {any} */ (window).plausible;
        if (typeof plausible !== "undefined" && !this.plausibleRouteDataSent) {
          plausible("Chat-message-route", { props: { route: response.data } });
          this.plausibleRouteDataSent = true;
        }
      } else if (response.type === "activity") {
        this.addActivity(response.data, "ai");
      } else if (response.type === "end") {
        sourcesContainer.showCitations(response.data.message_id);
        this.feedbackButtons?.showFeedback(response.data.message_id);
        this.#addFootnotes(streamedContent);
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
}
customElements.define("chat-message", ChatMessage);
