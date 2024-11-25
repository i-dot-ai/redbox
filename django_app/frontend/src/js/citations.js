import "./web-components/markdown-converter.js";

(() => {

  let plausible = /** @type {any} */ (window).plausible;
  if (typeof plausible !== "undefined") {
    plausible("citations-view");
  }

})();