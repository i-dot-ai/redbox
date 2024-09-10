// @ts-check

/** So completed docs can be added to this list */
class DocList extends HTMLElement {
  connectedCallback() {
    // Setup screen-reader announcements
    let screenReaderAnnouncements = document.createElement("div");
    /** @type {number} */
    let screenReaderAnnouncementsTimer;
    screenReaderAnnouncements.role = "alert";
    screenReaderAnnouncements.setAttribute("aria-live", "assertive");
    screenReaderAnnouncements.classList.add("govuk-visually-hidden");
    this.appendChild(screenReaderAnnouncements);

    document.body.addEventListener("doc-complete", (evt) => {
      // Move completed doc to this list
      const completedDoc = /** @type{CustomEvent} */ (evt).detail.closest(
        ".iai-doc-list__item"
      );
      completedDoc.querySelector("file-status").remove();
      this.querySelector("tbody")?.appendChild(completedDoc);

      // Announce doc is ready to screen-reader users
      const docName = completedDoc.querySelector(
        ".iai-doc-list__cell--file-name"
      ).textContent;
      screenReaderAnnouncements.textContent = `Processing Complete: ${docName}`;
      clearTimeout(screenReaderAnnouncementsTimer);
      screenReaderAnnouncementsTimer = window.setTimeout(() => {
        screenReaderAnnouncements.textContent = "";
      }, 1);
    });
  }
}
customElements.define("doc-list", DocList);
