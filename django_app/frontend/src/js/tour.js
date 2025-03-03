// @ts-check

// *** Interactive tour ***

if (window.location.pathname.includes("/chats/") && window.sessionStorage.getItem("tour") === "true" && window["introJs"]) {

  window.sessionStorage.removeItem("tour");

  window["introJs"]().setOptions({
    steps: [
      { 
        title: "Redbox tour",
        intro: "Welcome to Redbox! This is an interactive demo to help you get started.",
      },
      {
        title: "Redbox tour",
        element: "#message",
        intro: "This is where you type messages.",
      },
      {
        title: "Redbox tour",
        element: "canned-prompts",
        intro: "Or select a pre-written message to help you get started.",
      },
      {
        title: "Redbox tour",
        element: "send-message",
        intro: "Once you are ready, click on the Send button to send your message (or press the enter key after typing).",
      },
      {
        title: "Redbox tour",
        element: "canned-prompts",
        intro: "The response will appear in this area.",
      },
      {
        title: "Redbox tour",
        element: ".rb-chat-history",
        intro: "Previous chats will appear here.",
      },
      {
        title: "Redbox tour",
        element: "#new-chat-button",
        intro: "After you have received a response, you can continue with your chat, or start a new one by clicking the New chat button.",
      },
      {
        title: "Redbox tour",
        element: "attach-document",
        intro: "You can attach documents to your message by clicking the Add file button, or by dragging-and-dropping files on to the page.",
      },
      {
        title: "Redbox tour",
        element: "model-selector",
        intro: "You can select different Large Language Models (LLMs) to chat with.",
      },
      {
        title: "Redbox tour",
        element: ".iai-top-nav__link--user",
        intro: "By clicking on your intials in the header you can log out and access your details.",
      },
      {
        title: "Redbox tour",
        element: ".iai-footer__list",
        intro: "If you have any further questions, there are links to FAQs and support pages in the footer.",
      },
    ],
    nextLabel: "Next",
    prevLabel: "Previous",
    doneLabel: "Done",
    
  }).start();

  // Accessibility fix
  document.querySelector(".introjs-skipbutton")?.setAttribute("aria-label", "Skip the interactive demo");

}