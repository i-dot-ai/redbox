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
            <svg width="22" viewBox="0 0 24 24" focusable="false" aria-hidden="true">
                <path d="M22.088 10.651a2.07 2.07 0 0 0-1.937-1.636S16.2 9.015 15.96 9a5.017 5.017 0 0 0 1.242-3.168c0-2.194-.42-3.457-1.284-3.861a1.768 1.768 0 0 0-1.793.335l-.179.15v.232a7.073 7.073 0 0 1-1.174 3.496 8.993 8.993 0 0 1-2.49 2.649L7.96 12H7v-2H2v13h5v-2h1.796l2.47.966L18.19 22a2.22 2.22 0 0 0 2.045-1.166 1.755 1.755 0 0 0 .062-1.425 2.15 2.15 0 0 0 1.053-1.348 2.19 2.19 0 0 0-.262-1.713 2.253 2.253 0 0 0 .923-1.461 2.165 2.165 0 0 0-.445-1.672 2.705 2.705 0 0 0 .523-2.564zM6 22H3V11h3zm14.571-9.251l-.582.363.525.443a1.27 1.27 0 0 1 .508 1.175 1.359 1.359 0 0 1-.892 1.013l-.747.305.604.533a1.208 1.208 0 0 1 .395 1.227 1.167 1.167 0 0 1-.908.851l-.775.167.485.628a.858.858 0 0 1 .153.939 1.25 1.25 0 0 1-1.148.607h-6.646l-2.472-.966L7 20.007V13h1.473l2.448-3.395a9.933 9.933 0 0 0 2.683-2.867 8.134 8.134 0 0 0 1.328-3.772.654.654 0 0 1 .562-.089c.166.078.708.52.708 2.955a4.09 4.09 0 0 1-1.101 2.614 1.051 1.051 0 0 0-.237 1.06c.25.494.87.494 1.896.494h3.391c.524 0 .847.48.976.928a1.616 1.616 0 0 1-.556 1.821z"/>
                <path class="rb-response-feedback__thumb-fill" d="M 22.088 10.651 z M 6 22 H 3 V 11 h 3 z m 14.571 -9.251 l -0.582 0.363 l 0.525 0.443 a 1.27 1.27 0 0 1 0.508 1.175 a 1.359 1.359 0 0 1 -0.892 1.013 l -0.747 0.305 l 0.604 0.533 a 1.208 1.208 0 0 1 0.395 1.227 a 1.167 1.167 0 0 1 -0.908 0.851 l -0.775 0.167 l 0.485 0.628 a 0.858 0.858 0 0 1 0.153 0.939 a 1.25 1.25 0 0 1 -1.148 0.607 h -6.646 l -2.472 -0.966 L 7 20.007 V 13 h 1.473 l 2.448 -3.395 a 9.933 9.933 0 0 0 2.683 -2.867 a 8.134 8.134 0 0 0 1.328 -3.772 a 0.654 0.654 0 0 1 0.562 -0.089 c 0.166 0.078 0.708 0.52 0.708 2.955 a 4.09 4.09 0 0 1 -1.101 2.614 a 1.051 1.051 0 0 0 -0.237 1.06 c 0.25 0.494 0.87 0.494 1.896 0.494 h 3.391 c 0.524 0 0.847 0.48 0.976 0.928 a 1.616 1.616 0 0 1 -0.556 1.821 z"/>    
            </svg>
            <span class="feedback__negative">Sorry this didn't meed your expectations</span>
            <span class="feedback__positive">Thanks for the feedback</span>
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
