// @ts-check

class ChatHistory extends HTMLElement {

  /**
   * Creates a "Today" heading, if it doesn't already exist
   */
  #createTodayHeading() {
    // Create "Today" heading if it doesn't already exist
    let todayHeadingExists = false;
    const headings = this.querySelectorAll("h3");
    headings.forEach((heading) => {
      if (heading.textContent === "Today") {
        todayHeadingExists = true;
      }
    });
    if (!todayHeadingExists) {
      let newHeading = /** @type {HTMLTemplateElement} */ (this.querySelector("#template-chat_history_heading")).content.querySelector("h3");
      if (!newHeading) {
        return;
      }
      newHeading.textContent = "Today";
      this.prepend(newHeading);
    }
  }

  /**
   * Internal method for adding the list-item to the chat history
   * @param {string} chatId 
   * @param {string} title 
   */
  #createItem(chatId, title) {
    const newItem = /** @type {HTMLTemplateElement} */ (this.querySelector("#template-chat_history_item")).content.querySelector("li")?.cloneNode(true);
    let link = /** @type {HTMLElement} */ (newItem).querySelector("a");
    let deleteChatButton = /** @type {HTMLElement} */ (newItem).querySelector("delete-chat");
    if (!link) {
      return;
    }
    link.textContent = title;
    link.setAttribute("href", "/chats/${chatId");
    deleteChatButton?.setAttribute("data-chatid", chatId);
    this.querySelector("ul")?.prepend(/** @type {HTMLElement} */ (newItem));
  }

  /**
   * Adds an item to the chat history
   * @param {string} chatId 
   * @param {string} title 
   */
  addChat(chatId, title) {
    this.#createTodayHeading();
    this.#createItem(chatId, title.substring(0, 30));
  }

}

customElements.define("chat-history", ChatHistory);
