// @ts-check

document.querySelector(".js-tour-button")?.addEventListener("click", () => {
  window.sessionStorage.setItem("tour", "true");
  window.location.href = "/chats";
});
