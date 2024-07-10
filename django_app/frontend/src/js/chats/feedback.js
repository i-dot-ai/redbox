// @ts-check

class FeedbackButtons extends HTMLElement {
  showFeedback(messageId) {
    let collectedData = {
      rating: 0,
      text: "",
      chips: /** @type {string[]}*/ ([]),
    };

    const starIcon = `
        <svg width="25" height="25" viewBox="0 0 25 25" fill="none" focusable="false" aria-hidden="true">
            <path d="M12.0172 1.68381C12.1639 1.21711 12.8244 1.21711 12.9711 1.68381L15.1648 8.66018C15.3613 9.28511 15.9406 9.71024 16.5957 9.71024H23.7624C24.2428 9.71024 24.4468 10.3217 24.0626 10.6101L18.2088 15.0049C17.7002 15.3867 17.4877 16.0477 17.6784 16.6544L19.901 23.7227C20.0468 24.1863 19.5124 24.5643 19.1238 24.2726L13.3947 19.9714C12.8612 19.5708 12.1271 19.5708 11.5936 19.9714L5.86446 24.2726C5.47585 24.5643 4.94152 24.1863 5.08728 23.7227L7.30983 16.6544C7.50059 16.0477 7.28806 15.3867 6.77949 15.0049L0.925668 10.6101C0.5415 10.3217 0.745481 9.71024 1.22586 9.71024H8.3926C9.0477 9.71024 9.62702 9.28511 9.82353 8.66017L12.0172 1.68381Z" fill="currentColor" stroke="#BEBEBE"/>
        </svg>
    `;

    this.innerHTML = `
        <div class="feedback__container feedback__container--1">
            <h3 class="feedback__heading">Rate this response:</h3>
            <div class="feedback__star-container">
                <span class="feedback__star-help-text" aria-hidden="true">Not helpful</span>
                <button class="feedback__star-button" data-rating="1" type="button">
                    ${starIcon}
                    <span class="govuk-visually-hidden">1 star out of 5 (not helpful)</span>
                </button>
                <button class="feedback__star-button" data-rating="2" type="button">
                    ${starIcon}
                    <span class="govuk-visually-hidden">2 star out of 5</span>
                </button>
                <button class="feedback__star-button" data-rating="3" type="button">
                    ${starIcon}
                    <span class="govuk-visually-hidden">3 star out of 5</span>
                </button>
                <button class="feedback__star-button" data-rating="4" type="button">
                    ${starIcon}
                    <span class="govuk-visually-hidden">4 star out of 5</span>
                </button>
                <button class="feedback__star-button" data-rating="5" type="button">
                    ${starIcon}
                    <span class="govuk-visually-hidden">5 star out of 5 (very helpful)</span>
                </button>
                <span class="feedback__star-help-text" aria-hidden="true">Very helpful</span>
            </div>
        </div>
        <div class="feedback__container feedback__container--2" hidden>
            <div class="feedback__response-container">
                <img src="/static/icons/thumbs-up.svg" alt=""/>
                <span class="feedback__negative">Sorry this didn't meed your expectations</span>
                <span class="feedback__positive">Thanks for the feedback</span>
            </div>
            <button class="feedback__improve-response-btn">Help improve the response</button>
        </div>
        <div class="feedback__container feedback__container--3" hidden>
            <fieldset class="feedback__negative">
                <legend>How would you describe the response?</legend>
                <input class="feedback__chip" type="checkbox" id="chip1-negative-${messageId}"/>
                <label for="chip1-negative-${messageId}">Inaccurate</label>
                <input class="feedback__chip" type="checkbox" id="chip2-negative-${messageId}"/>
                <label for="chip2-negative-${messageId}">Incomplete</label>
                <input class="feedback__chip" type="checkbox" id="chip3-negative-${messageId}"/>
                <label for="chip3-negative-${messageId}">Bad quality</label>
            </fieldset>
            <fieldset class="feedback__positive">
                <legend>How would you describe the response?</legend>
                <input class="feedback__chip" type="checkbox" id="chip1-positive-${messageId}"/>
                <label for="chip1-positive-${messageId}">Accurate</label>
                <input class="feedback__chip" type="checkbox" id="chip2-positive-${messageId}"/>
                <label for="chip2-positive-${messageId}">Complete</label>
                <input class="feedback__chip" type="checkbox" id="chip3-positive-${messageId}"/>
                <label for="chip3-positive-${messageId}">Good quality</label>
            </fieldset>
            <label for="text-${messageId}">Or describe with your own words:</label>
            <textarea id="text-${messageId}" rows="1"></textarea>
            <button class="feedback_submit-btn" type="submit">Submit</button>
        </div>
        <div class="feedback__container feedback__container--4" hidden>
           <span>Thanks for helping improve this response</span>
           <button class="feedback__rate-again-btn">Rate response again</button> 
        </div>
    `;

    /**
     * @param {number} panelIndex - zero based
     */
    const showPanel = (panelIndex) => {
      let panels = this.querySelectorAll(".feedback__container");
      panels.forEach((panel) => {
        panel.setAttribute("hidden", "");
      });
      panels[panelIndex].removeAttribute("hidden");
      if (collectedData.rating >= 3) {
        panels[panelIndex].classList.remove("feedback__container--negative");
        panels[panelIndex].classList.add("feedback__container--positive");
      } else {
        panels[panelIndex].classList.add("feedback__container--negative");
        panels[panelIndex].classList.remove("feedback__container--positive");
      }
    };

    /* Panel 1 - stars rating */
    let starButtons = /** @type {NodeListOf<HTMLElement>} */ (
      this.querySelectorAll(".feedback__star-button")
    );
    starButtons.forEach((starButton, buttonIndex) => {
      starButton.addEventListener("click", () => {
        collectedData.rating = parseInt(starButton.dataset.rating || "0");
        fetch(`/ratings/${messageId}/`, {
          method: "POST",
          body: JSON.stringify(collectedData),
        });
        showPanel(1);
      });
      starButton.addEventListener("mouseover", () => {
        starButtons.forEach((btn) => {
          btn.classList.remove("feedback__star-button--hover");
        });
        for (let i = 0; i <= buttonIndex; i++) {
          starButtons[i].classList.add("feedback__star-button--hover");
        }
      });
      starButton.addEventListener("mouseleave", () => {
        starButtons.forEach((btn) => {
          btn.classList.remove("feedback__star-button--hover");
        });
      });
    });

    /* Panel 2 - help improve response */
    this.querySelector(".feedback__improve-response-btn")?.addEventListener(
      "click",
      () => {
        showPanel(2);
      }
    );

    /* Panel 3 - text and chips */
    this.querySelector(".feedback_submit-btn")?.addEventListener(
      "click",
      (evt) => {
        evt.preventDefault();
        /** @type {NodeListOf<HTMLInputElement>} */
        let chips = this.querySelectorAll(".feedback__chip");
        chips.forEach((chip) => {
          if (chip.checked) {
            const text = this.querySelector(`[for="${chip.id}"]`)?.textContent;
            if (text) {
              collectedData.chips.push(text);
            }
          }
        });
        collectedData.text = /** @type {HTMLTextAreaElement} */ (
          this.querySelector(`#text-${messageId}`)
        )?.value;
        fetch(`/ratings/${messageId}/`, {
          method: "POST",
          body: JSON.stringify(collectedData),
        });
        showPanel(3);
      }
    );

    /* Panel 4 - thank you */
    this.querySelector(".feedback__rate-again-btn")?.addEventListener(
      "click",
      () => {
        showPanel(0);
      }
    );
  }

  // If the messageID already exists (e.g. for SSR messages), render the feedback HTML immediately
  connectedCallback() {
    if (this.dataset.id) {
      this.showFeedback(this.dataset.id);
    }
  }
}
customElements.define("feedback-buttons", FeedbackButtons);
