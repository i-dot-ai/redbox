// @ts-check

class DocumentSelector extends HTMLElement {
  connectedCallback() {
    const documents = /** @type {NodeListOf<HTMLInputElement>} */ (
      this.querySelectorAll('input[type="checkbox"]')
    );

    const getSelectedDocuments = () => {
      let selectedDocuments = [];
      documents.forEach((document) => {
        if (document.checked) {
          selectedDocuments.push({
            id: document.value,
            name: this.querySelector(`[for="${document.id}"]`)?.textContent
          });
        }
      });
      const evt = new CustomEvent("selected-docs-change", {
        detail: selectedDocuments,
      });
      document.body.dispatchEvent(evt);
    };

    // update on page load
    getSelectedDocuments();

    // update on any selection change
    documents.forEach((document) => {
      document.addEventListener("change", getSelectedDocuments);
    });

    // listen for completed docs
    document.body.addEventListener("doc-complete", (evt) => {
      const completedDoc = /** @type{CustomEvent} */ (evt).detail.closest(
        ".govuk-checkboxes__item"
      );
      completedDoc.querySelector("file-status").remove();
      this.querySelector(".govuk-checkboxes")?.appendChild(completedDoc);
    });
  }
}
customElements.define("document-selector", DocumentSelector);
