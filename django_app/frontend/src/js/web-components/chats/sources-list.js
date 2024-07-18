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
