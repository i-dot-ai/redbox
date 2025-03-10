// @ts-check

mermaid.initialize({
  startOnLoad: false,
  flowchart: {
    htmlLabels: false
  }
});


window["runMermaid"] = async () => {
  
  await window.mermaid.run();
  
  // Due to having to remove the foreignObject elements, the spacing will be out without these adjustments
  let mermaidLabels = document.querySelectorAll("g.label");
    mermaidLabels.forEach((label) => {
      label.setAttribute("transform", "translate(0, 5)");
  });
  let mermaidTexts = document.querySelectorAll("g.label text");
  mermaidTexts.forEach((text) => {
    if (text.getAttribute("y") === "-10.1") {
      text.setAttribute("y", "16");
    }
  });

  // Apply inline styles directly in JavaScript (as they will be blocked by our CSP)
  /** @type {NodeListOf<SVGElement>} */
  let styledElements = document.querySelectorAll(".mermaid [style]");
  styledElements.forEach((element) => {
    const style = element.getAttribute("style");
    element.removeAttribute("style");
    style?.split(";").forEach((styleRule) => {
      if (styleRule.trim() !== "") {
        const [property, value] = styleRule.split(":");
        const camelCaseProperty = property
          .trim()
          .replace(/-([a-z])/g, (g) => g[1].toUpperCase());
        element.style[camelCaseProperty] = value.trim();
        try {
          element.setAttribute(
            property.trim(),
            value.replace("!important", "").trim()
          );
        } catch (err) {
          console.log(err);
        }
      }
    });
  });

};
window["runMermaid"]();
