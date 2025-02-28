// @ts-check

// *** Interactive tour ***


if (window["introJs"] && window.location.hash === "#tour" && window.location.pathname.includes("/chats/")) {

  window["introJs"]().setOptions({
    steps: [
      { 
        title: "Redbox interactive demo",
        intro: "Welcome to Redbox! This is an interactive demo to help you get started.",
      },
      {
        title: "Redbox interactive demo",
        element: "#message",
        intro: "This is where you type messages.",
      },
      {
        title: "Redbox interactive demo",
        element: "canned-prompts",
        intro: "Or select a pre-written message to help you get started.",
      },
      {
        title: "Redbox interactive demo",
        element: "send-message",
        intro: "Once you are ready, click on the Send button to send your message (or press the enter key after typing).",
      },
      {
        title: "Redbox interactive demo",
        element: "canned-prompts",
        intro: "The response will appear in this area.",
      },
      {
        title: "Redbox interactive demo",
        element: ".rb-chat-history",
        intro: "Previous chats will appear here.",
      },
      {
        title: "Redbox interactive demo",
        element: "#new-chat-button",
        intro: "After you have received a response, you can continue with your chat, or start a new one by clicking the New chat button.",
      },
      {
        title: "Redbox interactive demo",
        element: "attach-document",
        intro: "You can attach documents to your message by clicking the Add file button, or by dragging-and-dropping files on to the page.",
      },
      {
        title: "Redbox interactive demo",
        element: "model-selector",
        intro: "You can select different Large Language Models (LLMs) to chat with.",
      },
      {
        title: "Redbox interactive demo",
        element: ".iai-top-nav__link--user",
        intro: "By clicking on your intials in the header you can log out and access your details.",
      },
      {
        title: "Redbox interactive demo",
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