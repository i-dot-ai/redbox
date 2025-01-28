import "./web-components/chats/attach-document.mjs";
import "./web-components/chats/chat-controller.js";
import "./web-components/chats/chat-history.js";
import "./web-components/chats/chat-history-item.js";
import "./web-components/chats/chat-message.js";
import "./web-components/chats/chat-message-footer.mjs";
import "./web-components/chats/chat-title.js";
import "./web-components/chats/copy-text.js";
import "./web-components/chats/feedback-buttons.js";
import "./web-components/chats/markdown-converter.js";
import "./web-components/chats/message-input.js";
import "./web-components/chats/model-selector.mjs";
import "./web-components/chats/canned-prompts.mjs";
import "./web-components/chats/send-message.js";
import "./web-components/chats/exit-feedback.js";

import "./web-components/documents/document-container.mjs";
import "./web-components/documents/document-upload.mjs";
import "./web-components/documents/file-status.mjs";
import "./web-components/documents/upload-container.mjs";

document.addEventListener("chat-response-end", (evt) => {
  
  // Update URL when a new chat is created
  const sessionId = /** @type{CustomEvent} */ (evt).detail.session_id;
  const sessionTitle = /** @type{CustomEvent} */ (evt).detail.title;
  window.history.pushState({}, "", `/chats/${sessionId}`);

  // And add to chat history
  document.querySelector("chat-history").addChat(sessionId, sessionTitle);
});
