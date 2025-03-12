// @ts-check

/** @type {import ('../../node_modules/@types/dompurify/index.d.ts')} */
let DOMPurify = window["DOMPurify"];

// Create default policy
if (typeof window.trustedTypes !== "undefined") {
  window.trustedTypes.createPolicy("default", {
    createHTML: (to_escape) => {

      // We need to remove foreignObject elements (and therefore HTML elements contained within them) from the SVG
      if (to_escape.includes('id="mermaid-')) {
        to_escape = to_escape.replace(/foreignObject/g, "g");
        to_escape = to_escape.replace(/div/g, "g");
        to_escape = to_escape.replace(/span/g, "g");
        to_escape = to_escape.replace(/<p\b[^>]*>/g, '<text>');
        to_escape = to_escape.replace(/<\/p>/g, '</text>');
      }

      return DOMPurify.sanitize(to_escape, {
        RETURN_TRUSTED_TYPE: false,
        CUSTOM_ELEMENT_HANDLING: {
          tagNameCheck: (tagName) =>
            tagName === "loading-message" ||
            tagName === "markdown-converter",
          attributeNameCheck: (attr) => true,
          allowCustomizedBuiltInElements: true,
        },
      });
    }
  });
}
