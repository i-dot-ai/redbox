// @ts-check

mermaid.initialize({
  startOnLoad: false,
  flowchart: {
    htmlLabels: false
  }
});


// Due to having to remove the foreignObject elements, the spacing will be out without these adjustments
window["runMermaid"] = async () => {
  await window.mermaid.run();
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
};
window["runMermaid"]();
