// @ts-check

/** @type {import ('../../node_modules/@types/dompurify/index.d.ts')} */
let DOMPurify = window["DOMPurify"];

/** @type {import ('../../node_modules/@types/showdown/index.d.ts')} */
let showdown = window["showdown"];


class MarkdownConverter extends HTMLElement {
    connectedCallback() {
        let converter = new showdown.Converter({
            disableForced4SpacesIndentedSublists: true,
            headerLevelStart: 3
        });
        const html = converter.makeHtml(this.textContent || '');
        this.innerHTML = /** @type any */ (DOMPurify.sanitize(html, {RETURN_TRUSTED_TYPE: true}));
    }
}
customElements.define('markdown-converter', MarkdownConverter);
