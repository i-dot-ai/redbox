// @ts-check
import { html, nothing } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class ModelSelector extends RedboxElement {

  static properties = {
    options: { type: Array, attribute: "data-models" },
    expanded: { type: Boolean, state: true },
    selectedOption: {type: Number, state: true},
    activeOption: {type: Number, state: true}, // this is the currently highlighted option when using keyboard, so can be different to selectedOption
    keyboardInUse: {type: Boolean, state: true}
  };

  constructor() {
    super();
    this.options = [];
  }

  connectedCallback() {
    super.connectedCallback();
    this.selectedOption = 0;
    this.options.forEach((option, index) => {
      if (option.selected) {
        this.selectedOption = index;
      }
      this.activeOption = this.selectedOption;
    });
    this.classList.add("rb-model-selector");
  }

  render() {
    if (this.jsInitialised) {
      return html`
        <div class="rb-model-selector__label">Model: </div>
        <div class="rb-model-selector__select" @click=${this.#toggle} @keydown=${this.#keypress} @blur=${this.#blur} aria-controls="models-list" aria-expanded=${this.expanded ? "true" : "false"} aria-haspopup="listbox" aria-label="Model" role="combobox" tabindex="0" aria-activedescendant="model-option-${this.activeOption}">
          ${this.options[this.selectedOption].name}
          <span aria-hidden="true">${this.expanded ? "▲" : "▼"}</span>
        </div>
        <div class="rb-model-selector__list" id="models-list" role="listbox" aria-label="Model" hidden=${this.expanded ? nothing : "true"}>
          ${this.options.map(
            (option, index) => html`
              <div role="option" @click=${this.#clickOption} class="rb-model-selector__option ${index === this.activeOption ? 'rb-model-selector__option--active' : ''} ${this.keyboardInUse ? 'keyboard' : ''}" data-index=${index} id="model-option-${index}" aria-selected=${index === this.selectedOption ? "true" : "false"} data-value=${option.id}>
                <span>${option.name}</span>
                <span>${option.description}</span>
              </div>
          `)}
        </div>
        <input type="hidden" id="llm-selector" name="llm" value=${this.options[this.selectedOption].id}/>
        <input type="hidden" id="max-tokens" value=${this.options[this.selectedOption].max_tokens}/>
      `;
    }
    return html`
      <label class="govuk-body-s govuk-!-font-weight-bold" for="llm-selector">Model</label>
      <select id="llm-selector" name="llm" class="govuk-select govuk-!-margin-top-1">
        ${this.options.map(
          (option) => html`
            <option value=${option.id} selected=${option.selected || nothing}>
              ${option.name} (${option.description})
            </option>
        `)}
      </select>
    `;
  }

  #toggle() {
    this.expanded = !this.expanded;
    this.keyboardInUse = false;
  }

  #clickOption(evt) {
    const option = evt.target.closest(".rb-model-selector__option");
    this.selectedOption = parseInt(option.dataset.index);
    this.activeOption = this.selectedOption;
    this.expanded = false;
    (() => {
      let plausible = /** @type {any} */ (window).plausible;
      if (typeof plausible === "undefined") {
        return;
      }
      plausible("Model changed", { props: { model: this.options[this.selectedOption].name } });
      if (document.querySelectorAll(".rb-token-sizes").length > 0) {
        plausible("Model changed following token limit message");
      }
    })();
  }

  #selectOptionByLetter(letter) {
    let matchFound = false;
    this.options.forEach((option, index) => {
      if (!matchFound && option.name.toLowerCase().startsWith(letter.toLowerCase())) {
        this.activeOption = index;
        matchFound = true;
      }
    });
  }

  #keypress(evt) {
    if (this.expanded) {
      if (evt.key === "ArrowDown" && this.activeOption < this.options.length - 1) {
        evt.preventDefault();
        this.activeOption ++;
      } else if (evt.key === "ArrowUp" && this.activeOption > 0) {
        evt.preventDefault();
        this.activeOption --;
      } else if (evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        this.selectedOption = this.activeOption;
        this.expanded = false;
      } else if (evt.key === "Escape") {
        this.expanded = false;
      } else if (evt.key.length === 1) {
        this.#selectOptionByLetter(evt.key);
      }
    } else {
      if (evt.key === "ArrowDown" || evt.key === "ArrowUp" || evt.key === "Enter" || evt.key === " ") {
        evt.preventDefault();
        this.expanded = true;
        if (evt.key === "ArrowDown") {
          this.activeOption = 0;
        } else if (evt.key === "ArrowUp") {
          this.activeOption = this.options.length - 1;
        }
      } else if (evt.key.length === 1) {
        this.#selectOptionByLetter(evt.key);
        this.expanded = true;
      }
    }
    this.keyboardInUse = true;
  }

  #blur() {
    window.setTimeout(() => {
      this.expanded = false;
    }, 200);
  }

}
customElements.define("model-selector", ModelSelector);
