// @ts-check

class SourcesList extends HTMLElement {
  constructor() {
    super();
    this.sources = [];
  }

  /**
   * Adds a source to the current message
   * @param {string} fileName
   * @param {string} url
   */
  add = (fileName, url) => {
    this.sources.push({
      fileName: fileName,
      url: url,
    });

    let html = `
            <h3 class="iai-chat-bubble__sources-heading govuk-heading-s govuk-!-margin-bottom-1">Sources</h3>
            <div class="iai-display-flex-from-desktop">
            <ul class="govuk-list govuk-list--bullet govuk-!-margin-bottom-0">
        `;
    this.sources.forEach((source) => {
      html += `
                <li class="govuk-!-margin-bottom-0">
                    <a class="iai-chat-bubbles__sources-link govuk-link" href="${source.url}">${source.fileName}</a>
                </li>
            `;
    });
    html += `</div></ul>`;

    this.innerHTML = html;
  };

  /**
   * Shows to citations link/button
   * @param {string} chatId
   */
  showCitations = (chatId) => {
    if (!chatId) {
      return;
    }
    let link = document.createElement("a");
    link.classList.add(
      "iai-chat-bubble__citations-button",
      "govuk-!-margin-left-2"
    );
    link.setAttribute("href", `/citations/${chatId}`);
    link.textContent = "View information behind this answer";
    this.querySelector(".iai-display-flex-from-desktop")?.appendChild(link);
  };
}
customElements.define("sources-list", SourcesList);

class ChatMessage extends HTMLElement {
  connectedCallback() {
    const uuid = crypto.randomUUID();
    this.innerHTML = `
            <div class="iai-chat-bubble iai-chat-bubble--${
              this.dataset.role === "user" ? "right" : "left"
            } govuk-body {{ classes }}" data-role="{{ role }}" tabindex="-1">
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
                    ? `<div class="rb-loading-ellipsis govuk-body-s">
                        Loading
                        <span aria-hidden="true">.</span>
                        <span aria-hidden="true">.</span>
                        <span aria-hidden="true">.</span>
                    </div>`
                    : ""
                }
                <sources-list></sources-list>
                <div class="govuk-notification-banner govuk-notification-banner--error govuk-!-margin-bottom-3 govuk-!-margin-top-3" role="alert" aria-labelledby="notification-title-${uuid}" data-module="govuk-notification-banner" hidden>
                    <div class="govuk-notification-banner__header">
                        <h3 class="govuk-notification-banner__title" id="notification-title-${uuid}">Error</h3>
                    </div>
                    <div class="govuk-notification-banner__content">
                        <p class="govuk-notification-banner__heading"></p>
                    </div>
                </div>
            </div>
            <feedback-buttons></feedback-buttons>
        `;

    // Insert route_display HTML
    const routeTemplate = /** @type {HTMLTemplateElement} */ (
      document.querySelector("#template-route-display")
    );
    const routeClone = document.importNode(routeTemplate.content, true);
    this.querySelector(".iai-chat-bubble__header")?.appendChild(routeClone);
  }

  /**
   * Streams an LLM response
   * @param {string} message
   * @param {string[]} selectedDocuments
   * @param {string | undefined} sessionId
   * @param {string} endPoint
   * @param {HTMLElement} chatControllerRef
   */
  stream = (
    message,
    selectedDocuments,
    sessionId,
    endPoint,
    chatControllerRef
  ) => {
    let responseContainer = /** @type MarkdownConverter */ (
      this.querySelector("markdown-converter")
    );
    let sourcesContainer = /** @type SourcesList */ (
      this.querySelector("sources-list")
    );
    let feedbackContainer = this.querySelector("feedback-buttons");
    let responseLoading = /** @type HTMLElement */ (
      this.querySelector(".rb-loading-ellipsis")
    );
    let webSocket = new WebSocket(endPoint);
    let streamedContent = "";
    let sources = [];

    // Stop streaming on escape key press
    this.addEventListener("keydown", (evt) => {
      if (evt.key === "Escape" && this.dataset.status === "streaming") {
        this.dataset.status = "stopped";
        webSocket.close();
      }
    });

    webSocket.onopen = (event) => {
      webSocket.send(
        JSON.stringify({
          message: message,
          sessionId: sessionId,
          selectedFiles: selectedDocuments,
        })
      );
      this.dataset.status = "streaming";
    };

    webSocket.onerror = (event) => {
      responseContainer.innerHTML =
        "There was a problem. Please try sending this message again.";
      this.dataset.status = "error";
    };

    webSocket.onclose = (event) => {
      responseLoading.style.display = "none";
      if (this.dataset.status !== "stopped") {
        this.dataset.status = "complete";
      }
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
        responseContainer.update(streamedContent);
      } else if (response.type === "session-id") {
        chatControllerRef.dataset.sessionId = response.data;
      } else if (response.type === "source") {
        sourcesContainer.add(response.data.original_file_name, response.data.url);
      } else if (response.type === "route") {
        let route = this.querySelector(".iai-chat-bubble__route");
        let routeText = route?.querySelector(".iai-chat-bubble__route-text");
        if (route && routeText) {
          routeText.textContent = response.data;
          route.removeAttribute("hidden");
        }

        // send route to Plausible
        let plausible = /** @type {any} */ (window).plausible;
        if (typeof plausible !== "undefined") {
          plausible("Chat-message-route", {props: {route: response.data}});
        }
      } else if (response.type === "hidden-route") {
        // TODO(@rachaelcodes): remove hidden-route with new route design
        // https://technologyprogramme.atlassian.net/browse/REDBOX-419

        // send route to Plausible
        let plausible = /** @type {any} */ (window).plausible;
        if (typeof plausible !== "undefined") {
          plausible("Chat-message-route", {props: {route: response.data}});
        }
      } else if (response.type === "end") {
        sourcesContainer.showCitations(response.data.message_id);
        feedbackContainer.showFeedback(response.data.message_id);
        const chatResponseEndEvent = new CustomEvent("chat-response-end", {
          detail: {
            title: response.data.title,
            session_id: response.data.session_id
          }
        });
        document.dispatchEvent(chatResponseEndEvent);
      } else if (response.type === "error") {
        this.querySelector(".govuk-notification-banner")?.removeAttribute(
          "hidden"
        );
        this.querySelector(".govuk-notification-banner__heading").innerHTML =
            response.data;
      }
    };
  };
}
customElements.define("chat-message", ChatMessage);

class ChatController extends HTMLElement {
  connectedCallback() {
    const messageForm = this.closest("form");
    const textArea = /** @type {HTMLInputElement | null} */ (
      this.querySelector(".js-user-text")
    );
    const messageContainer = this.querySelector(".js-message-container");
    const insertPosition = this.querySelector(".js-response-feedback");
    const feedbackButtons = /** @type {HTMLElement | null} */ (
      this.querySelector("feedback-buttons")
    );
    let selectedDocuments = [];

    messageForm?.addEventListener("submit", (evt) => {
      evt.preventDefault();
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
      aiMessage.stream(
        userText,
        selectedDocuments,
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

class DocumentSelector extends HTMLElement {
  connectedCallback() {
    const documents = /** @type {NodeListOf<HTMLInputElement>} */ (
      this.querySelectorAll('input[type="checkbox"]')
    );

    const getSelectedDocuments = () => {
      let selectedDocuments = [];
      documents.forEach((document) => {
        if (document.checked) {
          selectedDocuments.push(document.value);
        }
      });
      const evt = new CustomEvent("selected-docs-change", {
        detail: selectedDocuments,
      });
      document.body.dispatchEvent(evt);
    };

    // update on page load
    getSelectedDocuments();

    // update on any selection change
    documents.forEach((document) => {
      document.addEventListener("change", getSelectedDocuments);
    });
  }
}
customElements.define("document-selector", DocumentSelector);

class ChatTitle extends HTMLElement {

  pencilIcon = `<svg width="25" height="24" viewBox="0 0 25 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                         <path d="M11.9766 4H4.97656C4.44613 4 3.93742 4.21071 3.56235 4.58579C3.18728 4.96086 2.97656 5.46957 2.97656 6V20C2.97656 20.5304 3.18728 21.0391 3.56235 21.4142C3.93742 21.7893 4.44613 22 4.97656 22H18.9766C19.507 22 20.0157 21.7893 20.3908 21.4142C20.7658 21.0391 20.9766 20.5304 20.9766 20V13" stroke="black" stroke-linecap="round" stroke-linejoin="round"/>
                         <path d="M19.4766 2.49998C19.8744 2.10216 20.414 1.87866 20.9766 1.87866C21.5392 1.87866 22.0787 2.10216 22.4766 2.49998C22.8744 2.89781 23.0979 3.43737 23.0979 3.99998C23.0979 4.56259 22.8744 5.10216 22.4766 5.49998L12.9766 15L8.97656 16L9.97656 12L19.4766 2.49998Z" stroke="black" stroke-linecap="round" stroke-linejoin="round"/>
                       </svg>`;

  connectedCallback() {
    this.innerHTML = `<div class="chat_title__container">
                        <h2 class="chat_title__heading govuk-visually-hidden" hidden>${this.dataset.title} ${this.pencilIcon}</h2>
                        <h2 class="chat_title__no_session_heading govuk-visually-hidden" hidden>Current chat</h2>
                        <label for="chat_title" class="govuk-visually-hidden">Chat Title</label>
                        <input type="text" class="chat_title__input govuk-visually-hidden" id="chat_title" maxlength=${this.dataset.titleLength} value="${this.dataset.title}" hidden/>
                      </div>`;

    this.heading = this.querySelector(".chat_title__heading");
    this.input = this.querySelector(".chat_title__input");

    this.heading.addEventListener("click", this.switchToEdit);

    this.input.addEventListener("keydown", (e) => {
          switch (e.key) {
            case "Escape":
              this.escaped = true;
              this.input.value = this.dataset.title;
              this.switchToShow();
              return true;
            default:
              return true;
          }
        }
    )
    this.input.addEventListener("change", (e) => {
      if (!this.escaped) {
        this.update();
      }
    });
    this.input.addEventListener("blur", (e) => {
      this.switchToShow();
    });

    if (!this.dataset.sessionId) {
      document.addEventListener("chat-response-end", this.onFirstResponse)
    }

    this.switchToShow()
  }

  showElement(element) {
    element.removeAttribute("hidden");
    element.classList.remove("govuk-visually-hidden");
  }

  hideElement(element) {
    element.setAttribute("hidden", "");
    element.classList.add("govuk-visually-hidden");
  }

  switchToShow = () => {
    if (this.dataset.sessionId) {
      this.showElement(this.heading);
    } else {
      this.hideElement(this.heading);
    }
    this.hideElement(this.input);
  }

  switchToEdit = () => {
    this.escaped = false;
    this.hideElement(this.heading);
    this.showElement(this.input);
    this.input.focus();
  }

  onFirstResponse = (e) => {
    this.dataset.title = e.detail.title;
    this.input.value = e.detail.title;
    this.heading.innerText = `${e.detail.title}`;
    this.heading.innerHTML += ` ${this.pencilIcon}`;
    this.dataset.sessionId = e.detail.session_id;
    document.removeEventListener("chat-response-end", this.onFirstResponse);
    this.switchToShow();
  }

  update = () => {
    const newTitle = this.input.value;
    console.log(`updating chat title to "${newTitle}"`);
    this.send(newTitle)
    this.dataset.title = newTitle;
    this.heading.innerText = `${newTitle}`;
    this.heading.innerHTML += ` ${this.pencilIcon}`;
    this.switchToShow();
  }

  send = (newTitle) => {
    const csrfToken =
        /** @type {HTMLInputElement | null} */ (
        document.querySelector('[name="csrfmiddlewaretoken"]')
    )?.value || "";
    fetch(`/chat/${this.dataset.sessionId}/title/`, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
      body: JSON.stringify({name: newTitle}),
    })
  }
}

customElements.define("chat-title", ChatTitle);
