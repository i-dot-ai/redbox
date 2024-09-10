import "./web-components/chats/chat-controller.js";
import "./web-components/chats/chat-message.js";
import "./web-components/chats/chat-title.js";
import "./web-components/chats/copy-text.js";
import "./web-components/chats/document-selector.js";
import "./web-components/chats/feedback-buttons.js";
import "./web-components/markdown-converter.js";
import "./web-components/chats/message-input.js";
import "./web-components/chats/sources-list.js";
import "./web-components/chats/canned-prompts";
import "./web-components/chats/send-message.js";
import "./web-components/documents/file-status.js";

// Update URL when a new chat is created
document.addEventListener("chat-response-end", (evt) => {
  const sessionId = /** @type{CustomEvent} */ (evt).detail.session_id;
  window.history.pushState({}, "", `/chats/${sessionId}`);
});
