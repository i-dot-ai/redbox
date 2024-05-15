// @ts-check

/** @type {import ('../../node_modules/@types/dompurify/index.d.ts')} */
let DOMPurify = window["DOMPurify"];

/** @type {import ('../../node_modules/@types/showdown/index.d.ts')} */
let showdown = window["showdown"];


class MarkdownConverter extends HTMLElement {
    
    /**
     * Takes markdown and inserts as HTML
     * @param {string} markdown 
     */
    update(markdown) {
        let converter = new showdown.Converter({
            disableForced4SpacesIndentedSublists: true,
            headerLevelStart: 3,
            tables: true
        });
        const html = converter.makeHtml(markdown);
        this.innerHTML = /** @type any */ (DOMPurify.sanitize(html, {RETURN_TRUSTED_TYPE: true}));
    }

    connectedCallback() {
        this.update(this.textContent || '');
    }

    
}
customElements.define('markdown-converter', MarkdownConverter);
