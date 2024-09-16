// @ts-check

class ExitFeedback extends HTMLElement {
  constructor() {
    super();
    this.formData = new FormData();
  }
  connectedCallback() {
    this.innerHTML = `
      <form class="exit-feedback__panel" id="exit-feedback__panel">
        <div class="exit-feedback__page">
          <p tabindex="-1">Did Redbox do what you needed it to in this chat?</p>
          <button type="button" class="exit-feedback__button-yes">
            Yes
            <span class="visually-hidden">Redbox did what I needed it to in this chat</span>
          </button>
          <button type="button" class="exit-feedback__button-no">
            No
            <span class="visually-hidden">Redbox didn't do what I needed it to in this chat</span>
          </button>
        </div>
        <div class="exit-feedback__page">
          <button type="button" class="exit-feedback__back-button">Back</button>
          <fieldset>
            <legend>Did Redbox help save you time?</legend>
            <div>
              <input type="radio" id="exit-feedback__input-time-yes" name="saved_time" value="Yes"/>
              <label for="exit-feedback__input-time-yes">Yes</label>
            </div>
            <div>
              <input type="radio" id="exit-feedback__input-time-no" name="saved_time" value="No"/>
              <label for="exit-feedback__input-time-no">No</label>
            </div>
          </fieldset>
          <fieldset>
            <legend>Did Redbox help to improve your work?</legend>
            <div>
              <input type="radio" id="exit-feedback__input-improve-work-yes" name="improved_work" value="Yes"/>
              <label for="exit-feedback__input-improve-work-yes">Yes</label>
            </div>
            <div>
              <input type="radio" id="exit-feedback__input-improve-work-no" name="improved_work" value="No"/>
              <label for="exit-feedback__input-improve-work-no">No</label>
            </div>
          </fieldset>
          <label for="exit-feedback__input-notes">Do you want to tell us anything further?</label>
          <input type="text" id="exit-feedback__input-notes" name="notes"/>
          <button type="button" class="exit-feedback__send-button">Send</button>
        </div>
        <div class="exit-feedback__page">
          <p class="govuk-body" tabindex="-1">
            <span class="govuk-body-l govuk-!-display-block govuk-!-margin-bottom-0">Thanks</span>
            you’re helping improve Redbox
          </p>
        </div>
      </form>
      <button type="button" class="exit-feedback__toggle-button" aria-expanded="false" aria-controls="exit-feedback__panel">
        <span class="exit-feedback__toggle-button-text">Feedback</span>
      </button>
    `;

    const toggleButton = this.querySelector(".exit-feedback__toggle-button");
    toggleButton?.addEventListener("click", () => {
      if (toggleButton.getAttribute("aria-expanded") === "true") {
        toggleButton.setAttribute("aria-expanded", "false");
      } else {
        toggleButton.setAttribute("aria-expanded", "true");
        this.#changePage(0);
      }
    });

    // close menu if focus moves out of it
    let lastInteractionWasKeyboard = false;
    document.addEventListener("keydown", () => {
      lastInteractionWasKeyboard = true;
    });
    document.addEventListener("mousedown", () => {
      lastInteractionWasKeyboard = false;
    });
    this.addEventListener("focusout", () => {
      window.setTimeout(() => {
        if (
          !this.contains(document.activeElement) &&
          lastInteractionWasKeyboard
        ) {
          toggleButton?.setAttribute("aria-expanded", "false");
        }
      }, 100);
    });
    // close menu if user clicks away from it
    document.body.addEventListener("click", (evt) => {
      const targetElement = /** @type {HTMLElement | null} */ (evt.target);
      if (!targetElement?.closest(".exit-feedback")) {
        toggleButton?.setAttribute("aria-expanded", "false");
      }
    });

    // page 1
    this.#changePage(0);
    this.querySelector(".exit-feedback__button-yes")?.addEventListener(
      "click",
      () => {
        this.formData.set("achieved", "Yes");
        this.#changePage(1);
        this.#sendFeedback();
      }
    );
    this.querySelector(".exit-feedback__button-no")?.addEventListener(
      "click",
      () => {
        this.formData.set("achieved", "No");
        this.#changePage(1);
        this.#sendFeedback();
      }
    );

    // page 2
    this.querySelector(".exit-feedback__back-button")?.addEventListener(
      "click",
      () => {
        this.#changePage(0);
      }
    );
    this.querySelector(".exit-feedback__send-button")?.addEventListener(
      "click",
      () => {
        const form = this.querySelector("form");
        if (!form) {
          return;
        }
        for (let [key, value] of new FormData(form).entries()) {
          this.formData.set(key, value);
        }
        this.#changePage(2);
        this.#sendFeedback();
      }
    );
  }

  /**
   * @param {number} newPage zero-based
   */
  #changePage(newPage) {
    /** @type {NodeListOf<HTMLElement>} */
    let pages = this.querySelectorAll(".exit-feedback__page");
    pages.forEach((page, pageIndex) => {
      if (pageIndex === newPage) {
        page.style.display = "block";
        window.setTimeout(() => {
          /** @type {HTMLElement | null} */
          const firstInteractiveElement = page.querySelector(
            '[tabindex="-1"], button'
          );
          firstInteractiveElement?.focus();
        }, 100);
      } else {
        page.style.display = "none";
      }
    });
  }

  async #sendFeedback() {
    try {
      await fetch(`/chats/${this.dataset.chatid}/update-chat-feedback`, {
        method: "POST",
        headers: {
          "X-CSRFToken": this.dataset.csrf || "",
        },
        body: this.formData,
      });
    } catch (err) {
      console.log("Error sending exit feedback data", err);
    }
  }
}
customElements.define("exit-feedback", ExitFeedback);
