// @ts-check

class ActivityButton extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <button type="button">+ Show all activity</button>
    `;

    let button = this.querySelector("button");
    button?.addEventListener("click", () => {
      if (!button) {
        return;
      }
      const expanded = button?.getAttribute("expanded") === "true" ? false : true;
      button.setAttribute("expanded", expanded ? "true" : "false");
      button.textContent = expanded ? "- Hide all activity" : "+ Show all activity";
    });

  }

}
customElements.define("activity-button", ActivityButton);
