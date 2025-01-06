// @ts-check
import { LitElement, html, nothing } from "lit";
import { RedboxElement } from "../redbox-element.mjs";

export class ModelSelector extends RedboxElement {

  static properties = {
    options: { type: Array, attribute: "data-options" },
  };

  render() {
    return html`
      <label class="govuk-body-s govuk-!-font-weight-bold" for="llm-selector">Model</label>
      <select id="llm-selector" name="llm" class="govuk-select govuk-!-margin-top-1">
        ${this.options.map(
          (option) => html`
            <option value=${option.id} selected=${option.selected || nothing}>
              ${option.name} (${ option.description })
            </option>
        `)}
      </select>
    `;
  }

  //  

}
customElements.define("model-selector", ModelSelector);
