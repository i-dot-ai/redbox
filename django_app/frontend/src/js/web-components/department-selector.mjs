// @ts-check
import { html } from "lit";
import { RedboxElement } from "./redbox-element.mjs";

class DepartmentSelector extends RedboxElement {

  static properties = {
    selectedDepartment: { type: String, state: true },
    departments: { type: Array, state: true },
    businessUnits: { type: Array, state: true },
  };

  constructor() {
    super();

    // set defaults
    this.departments = [];
    this.businessUnits = [];
    this.selectedDepartment = "";

    // pull out options from existing <select> element
    let businessUnitOptions = this.querySelectorAll("option");
    businessUnitOptions.forEach((option) => {
      let optionSplit = option.textContent?.split(" - ");
      if (optionSplit?.length !== 2) {
        return;
      }
      if (!this.departments.includes(optionSplit[0])) {
        this.departments.push(optionSplit[0]);
      }
      this.businessUnits.push({
        department: optionSplit[0],
        businessUnit: optionSplit[1],
        value: option.value,
      });
    });

  }
  
  render() {
    return html`
      <div class="govuk-form-group">
        <label class="govuk-label" for="department">
          What Department are you part of
        </label>
        <select class="govuk-select" id="department" @change=${this.#changeDepartment}>
          <option value="">-- Please select --</option>
          ${this.departments.map((department) => html`
            <option>${department}</option>
          `)}
        </select>
      </div>
      ${this.selectedDepartment ? html`
        <div class="govuk-form-group">
          <label class="govuk-label" for="id_business_unit">
            What Business Unit are you part of
          </label>
          <select name="business_unit" class="govuk-select" id="id_business_unit">
            <option value="">-- Please select --</option>
            ${this.businessUnits.filter((bu) => bu.department === this.selectedDepartment).map((bu) => html`
              <option value="${bu.value}">${bu.businessUnit}</option>
            `)}
          </select>
        </div>
      ` : ""}
    `;
  }

  #changeDepartment(evt) {
    this.selectedDepartment = evt.target.value;
  }

}
customElements.define("department-selector", DepartmentSelector);
