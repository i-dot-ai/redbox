//@ts-check

//
// For guidance on how to add JavaScript see:
// https://prototype-kit.service.gov.uk/docs/adding-css-javascript-and-images
//

/*
window.GOVUKPrototypeKit.documentReady(() => {
  // Add JavaScript here
});
*/


class sourceSelector extends HTMLElement {

  // let server know when selection changes
  connectedCallback() {
    let radioButtons = this.querySelectorAll('input');
    radioButtons.forEach((radioButton) => {
      radioButton.addEventListener('click', () => {
        fetch(`/toggle-data-source?source=${radioButton.value}`);
      });
      // to ensure server has default value (as it's also based on number of docs)
      if (radioButton.checked) {
        fetch(`/toggle-data-source?source=${radioButton.value}`);
      }
    });
  }

}
customElements.define('source-selector', sourceSelector);



class dataSources extends HTMLElement {
  connectedCallback() {
    
    this.type = this.dataset.type;
    /** @type {NodeListOf<HTMLInputElement>} */
    this.checkBoxes = this.querySelectorAll('input[type="checkbox"]');
    /** @type {HTMLAnchorElement|null} */
    this.buttonsContainer = this.querySelector('.js-global-doc-buttons');

    // Check whether the Summarise and Chat buttons should be visible
    const checkGlobalButtonsVisibility = () => {
      if (!this.buttonsContainer) {
        return;
      }
      let selectedCount = 0;
      this.checkBoxes?.forEach((checkBox, index) => {
        if (checkBox.checked) {
          selectedCount ++;
        }
      });
      if (selectedCount >= 1) {
        this.buttonsContainer.style.display = 'inline-block';
      } else {
        this.buttonsContainer.style.display = 'none';
      }
    };
    checkGlobalButtonsVisibility();

    // Update server every time a checkbox is selected/deselected
    this.checkBoxes.forEach((checkBox, index) => {
      checkBox.addEventListener('click', () => {
        const url = `/toggle-document-selection?index=${index}&selected=${checkBox.checked}&type=${this.type}`;
        fetch(url, {method: 'POST'});
        checkGlobalButtonsVisibility();
      });
    });

  }
}
customElements.define('data-sources', dataSources);



class docStatus extends HTMLElement {

  // let server know when selection changes
  connectedCallback() {
    
    const SPEED = 400; // time in milliseconds to increase by x%
    this.processedPercent = parseInt(this.dataset.processed || '0');
    this.docIndex = this.dataset.index;
    this.el = this.querySelector('strong');
    
    this.parentElement?.parentElement?.classList.add('iai-processing');

    const increasePercentage = () => {
      
      if (!this.processedPercent) {
        this.processedPercent = 0;
      }
      this.processedPercent += Math.floor(Math.random() * 15);
      if (this.processedPercent > 100) {
        this.processedPercent = 100;
      }

      // send update to server
      fetch(`/processing-doc-update?doc-index=${this.docIndex}&process-percent=${this.processedPercent}`);

      // display changes
      if (this.el) {
        if (this.processedPercent < 100) {
          this.el.classList.add('govuk-tag--yellow');
          this.el.textContent = `Processing: ${this.processedPercent}%`;
        } else {
          this.el.classList.remove('govuk-tag--yellow');
          this.el.textContent = 'Ready';
          this.parentElement?.parentElement?.classList.remove('iai-processing');
        }
      }

      if (this.processedPercent < 100) {
        window.setTimeout(increasePercentage, SPEED);
      }

    };
    increasePercentage();
  }

}
customElements.define('doc-status', docStatus);
