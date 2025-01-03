// @ts-check

/** @type {import ('showdown')} */
let showdown = window["showdown"];

export class MarkdownConverter extends HTMLElement {
  /**
   * Takes markdown and inserts as HTML
   * @param {string} markdown
   */
  update(markdown) {
    let converter = new showdown.Converter({
      disableForced4SpacesIndentedSublists: true,
      headerLevelStart: 3,
      tables: true,
    });
    // escape any user-submitted HTML
    if (this.dataset.role === "user") {
      // escape the HTML tags
      markdown = markdown.replace(/</g, '&lt;').replace(/>/g, '&gt;');
      // mark them as code - flaky (because sometimes the HTML will be incomplete) so commented out for now
      //markdown = markdown.replace(/&lt;([\w-]+)&gt;/g, '<span class="code">&lt;$1&gt;</span>');
    }
    this.innerHTML = converter.makeHtml(markdown);
  }

  connectedCallback() {
    this.update(this.textContent || "");
  }
}
customElements.define("markdown-converter", MarkdownConverter);
