// @ts-check

class ChatHistoryItem extends HTMLElement {

  constructor() {
    super();
    this.initialised = false;
    /** @type {HTMLButtonElement | null} */
    this.toggleButton = this.querySelector("button[aria-expanded]");
    this.chatLink = /** @type {HTMLAnchorElement} */ (this.querySelector(".rb-chat-history__link"));
  }

  connectedCallback() {
    // So we don't rebind event listeners if this ChatHistoryItem moves
    if (!this.initialised) {
      this.#addEventListeners();
    }
    this.initialised = true;
  }

  #addEventListeners = () => {
    
    this.toggleButton?.addEventListener("click", () => {
      if (!this.toggleButton) {
        return;
      }
      if (this.toggleButton.getAttribute("aria-expanded") === "true") {
        this.toggleButton.setAttribute("aria-expanded", "false");
      } else {
        this.#changePage("1");
        this.toggleButton.setAttribute("aria-expanded", "true");
      }
    });

    this.querySelector('[data-action="delete"]')?.addEventListener("click", () => {
      this.#changePage("2");
      deleteButton.focus();
    });
    this.querySelector('[data-action="rename"]')?.addEventListener("click", () => {
      this.toggleButton?.setAttribute("aria-expanded", "false");
      this.#toggleChatTitleEdit(true);
    });
    this.querySelector('[data-action="print"]')?.addEventListener("click", this.#printChat);

    let deleteButton = /** @type {HTMLButtonElement} */ (this.querySelector('[data-action="delete-confirm"]'));
    deleteButton.addEventListener("click", async () => {
      deleteButton.disabled = true;
      this.#deleteChat();
      // move focus to nearest item
      let listItem = this.closest("li");
      if (listItem?.nextElementSibling) {
        /** @type {HTMLAnchorElement | null} */ (listItem.nextElementSibling.querySelector(".rb-chat-history__link"))?.focus();
      } else if (listItem?.previousElementSibling) {
        /** @type {HTMLAnchorElement | null} */ (listItem.previousElementSibling.querySelector(".rb-chat-history__link"))?.focus();
      } else {
        /** @type {HTMLAnchorElement | null} */ (document.querySelector("#new-chat-button"))?.focus();
      }
    });
    this.querySelector('[data-action="delete-cancel"]')?.addEventListener("click", () => {
      this.toggleButton?.setAttribute("aria-expanded", "false");
      this.toggleButton?.focus();
    });

    let chatTitleInput = this.querySelector("input");
    if (!chatTitleInput) {
      return;
    }
    chatTitleInput.addEventListener("change", () => {
      if (!chatTitleInput) {
        return false;
      }
      this.#toggleChatTitleEdit(false);
      this.#updateChatTitle(chatTitleInput.value, true);
    });
    chatTitleInput.addEventListener("blur", () => {
      this.#toggleChatTitleEdit(false);
    });
    chatTitleInput.addEventListener("keydown", (evt) => {
      if (!chatTitleInput) {
        return false;
      }
      switch (/** @type {KeyboardEvent} */ (evt).key) {
        case "Escape":
          chatTitleInput.value = this.dataset.title || "";
          this.#toggleChatTitleEdit(false);
          return true;
        case "Enter":
          evt.preventDefault();
          this.#updateChatTitle(chatTitleInput.value, true);
          this.#toggleChatTitleEdit(false);
          return true;
        default:
          return true;
      }
    });

    document.addEventListener("chat-title-change", (evt) => {
      let evtData = /** @type {object} */ (evt).detail;
      if (evtData.sender !== "chat-history-item" && evtData.session_id === this.dataset.chatid) {
        this.chatLink.textContent = evtData.title;
        this.#updateChatTitle(evtData.title, false);
      }
    });

  };

  /**
   * @param {string} pageNumber 
   */
  #changePage = (pageNumber) => {
    /** @type {NodeListOf<HTMLElement>} */
    let pages = this.querySelectorAll("[data-page]");
    pages.forEach((page, pageIndex) => {
      if (page.dataset.page === pageNumber) {
        page.style.display = "block";
      } else {
        page.style.display = "none";
      }
    });
  };

  #deleteChat = async () => {
    const csrfToken =
        /** @type {HTMLInputElement | null} */ (
        document.querySelector('[name="csrfmiddlewaretoken"]')
    )?.value || "";
    await fetch(`/chats/${this.dataset.chatid}/delete-chat`, {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
    });
    if (this.dataset.iscurrentchat === "true") {
      window.location.href = "/chats";
    } else {
      this.closest("li")?.remove();
    }
  };

  /**
   * @param {boolean} show 
   */
  #toggleChatTitleEdit = (show) => {
    let chatTitleEdit = /** @type {HTMLElement} */ (this.querySelector(".rb-chat-history__text-input"));
    let chatTitleInput = /** @type {HTMLInputElement} */ (chatTitleEdit.querySelector("input"));
    if (show) {
      chatTitleInput.value = this.chatLink.textContent || "";
      this.chatLink.style.display = "none";
      chatTitleEdit.style.display = "block";
      chatTitleInput?.focus();
    } else {
      this.chatLink.textContent = chatTitleInput.value;
      chatTitleEdit.style.display = "none";
      this.chatLink.style.display = "block";
      this.toggleButton?.focus();
    }
  };

  /**
   * @param {string} newTitle 
   * @param {boolean} publishChanges Whether to let other components know about this change
   */
  #updateChatTitle = (newTitle, publishChanges) => {
    const csrfToken =
      /** @type {HTMLInputElement | null} */ (
      document.querySelector('[name="csrfmiddlewaretoken"]')
    )?.value || "";

    if (!this.dataset.titleUrl || !this.dataset.chatid) {
      return;
    }

    fetch(this.dataset.titleUrl.replace("00000000-0000-0000-0000-000000000000", this.dataset.chatid), {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
      body: JSON.stringify({name: newTitle}),
    });
    if (publishChanges) {
      const chatTitleChangeEvent = new CustomEvent("chat-title-change", {
        detail: {
          title: newTitle,
          session_id: this.dataset.chatid,
          sender: "chat-history-item"
        },
      });
      document.dispatchEvent(chatTitleChangeEvent);
    }
  };

  #printChat = () => {
    const url = this.querySelector(".rb-chat-history__link").href;
    const printFrame = document.createElement("iframe");
    printFrame.addEventListener("load", () => {
      const closePrint = () => {
        document.body.removeChild(printFrame);
      };
      printFrame.contentWindow.addEventListener("beforeunload", closePrint);
      printFrame.contentWindow.addEventListener("afterprint", closePrint);
      printFrame.contentWindow?.print();
      printFrame.style.display = "none";
    });
    printFrame.src = url;
    document.body.appendChild(printFrame);
  };

}

customElements.define("chat-history-item", ChatHistoryItem);
