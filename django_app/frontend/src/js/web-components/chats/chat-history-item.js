// @ts-check

class ChatHistoryItem extends HTMLElement {

  constructor() {
    super();
    this.initialised = false;
  }

  connectedCallback() {
    // So we don't rebind event listeners if this ChatHistoryItem moves
    if (!this.initialised) {
      this.#addEventListeners();
    }
    this.initialised = true;
  }

  #addEventListeners = () => {
    
    let toggleButton = this.querySelector("button[aria-expanded]");
    toggleButton?.addEventListener("click", () => {
      if (!toggleButton) {
        return;
      }
      if (toggleButton.getAttribute("aria-expanded") === "true") {
        toggleButton.setAttribute("aria-expanded", "false");
      } else {
        this.#changePage("1");
        toggleButton.setAttribute("aria-expanded", "true");
      }
    });

    this.querySelector('[data-action="delete"]')?.addEventListener("click", () => {
      this.#changePage("2");
    });
    this.querySelector('[data-action="rename"]')?.addEventListener("click", () => {
      toggleButton?.setAttribute("aria-expanded", "false");
    });

    let deleteButton = /** @type {HTMLButtonElement} */ (this.querySelector('[data-action="delete-confirm"]'));
    deleteButton.addEventListener("click", async () => {
      deleteButton.disabled = true;
      this.#deleteChat();
    });
    this.querySelector('[data-action="delete-cancel"]')?.addEventListener("click", () => {
      this.#changePage("1");
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

}

customElements.define("chat-history-item", ChatHistoryItem);
