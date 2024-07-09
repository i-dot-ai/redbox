(() => {
  class ToggleButton extends HTMLElement {
    connectedCallback() {
      const e = this.querySelector("button");
      e?.addEventListener("click", () => {
        const t = "true" == e.getAttribute("aria-expanded");
        e.setAttribute("aria-expanded", t ? "false" : "true");
      });
    }
  }
  customElements.define("toggle-button", ToggleButton);
  class MobileDropDown extends HTMLElement {
    connectedCallback() {
      this.classList.add("initialised"),
        document.body.addEventListener("toggle-mobile-menu", (e) => {
          e.detail
            ? (this.timer && window.clearTimeout(this.timer),
              this.querySelector("nav")?.removeAttribute("hidden"),
              (this.style.maxHeight = `${this.scrollHeight}px`))
            : ((this.style.maxHeight = "0px"),
              (this.timer = window.setTimeout(() => {
                this.querySelector("nav")?.setAttribute("hidden", "");
              }, 700)));
        });
    }
  }
  customElements.define("mobile-drop-down", MobileDropDown);
  class HamburgerButton extends HTMLElement {
    constructor() {
      super(), (this.expanded = !1), (this.firstToggle = !0);
    }
    toggle(e) {
      const t = new CustomEvent("toggle-mobile-menu", { detail: e });
      window.setTimeout(() => {
        document.body.dispatchEvent(t);
      }, 1),
        this.firstToggle
          ? (this.firstToggle = !1)
          : (this.classList.add("iai-top-nav__mobile-button--initiated"),
            this.setAttribute("aria-expanded", e.toString()));
    }
    connectedCallback() {
      (this.role = "button"),
        (this.tabIndex = 0),
        this.classList.add("js-init"),
        this.setAttribute("aria-expanded", "false"),
        (this.innerHTML =
          '\n        <span class="govuk-visually-hidden">Menu</span>\n        <span class="iai-top-nav__mobile-button-bar iai-top-nav__mobile-button-bar--1"></span>\n        <span class="iai-top-nav__mobile-button-bar iai-top-nav__mobile-button-bar--2"></span>\n        <span class="iai-top-nav__mobile-button-bar iai-top-nav__mobile-button-bar--3"></span>\n    '),
        this.addEventListener("click", () => {
          (this.expanded = !this.expanded), this.toggle(this.expanded);
        }),
        this.addEventListener("keydown", (e) => {
          ("Enter" !== e.key && " " !== e.key) ||
            ((this.expanded = !this.expanded), this.toggle(this.expanded));
        });
      const checkMobileView = () =>
        (() => {
          window.innerWidth < 1020
            ? ((this.expanded = !1), this.toggle(!1))
            : ((this.expanded = !0), this.toggle(!0));
        })();
      checkMobileView(), window.addEventListener("resize", checkMobileView);
    }
  }
  customElements.define("hamburger-button", HamburgerButton);
  class NotificationBanner extends HTMLElement {
    connectedCallback() {
      let e = document.createElement("button");
      e.classList.add("govuk-notification-banner__close-btn"),
        (e.innerHTML =
          '\n            <span class="govuk-visually-hidden">Close notification</span>\n            <svg width="20" height="20" viewBox="0 0 16 16" fill="none" aria-hidden="true" focusable="false">\n                <path d="M12 4L4 12" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"/>\n                <path d="M4 4L12 12" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"/>\n            </svg>\n        '),
        window.setTimeout(() => {
          this.querySelector(".govuk-notification-banner__header")?.appendChild(
            e
          );
        }, 1),
        e.addEventListener("click", () => {
          this.remove();
        });
    }
  }
  customElements.define("notification-banner", NotificationBanner);
  class ToolTip extends HTMLElement {
    connectedCallback() {
      window.setTimeout(() => {
        const e = crypto.randomUUID();
        let t = this.querySelector(".iai-tooltip__button"),
          n = this.querySelector(".iai-tooltip__content"),
          i = "";
        if (!t || !n) return;
        const showTooltip = (e) => {
            (i = e), n && (n.style.display = "block");
          },
          hideTooltip = (e) => {
            n &&
              ((e !== i &&
                "all" !== e &&
                "mouseover" === e &&
                "keyboard" !== i) ||
                ((n.style.display = "none"), (i = "")));
          };
        t.setAttribute("role", "tooltip"),
          t.setAttribute("aria-describedby", `tooltip-content-${e}`),
          (n.id = `tooltip-content-${e}`),
          this.addEventListener("mouseover", () => {
            showTooltip("mouse");
          }),
          this.addEventListener("mouseleave", () => {
            "mouse" === i && hideTooltip("mouse");
          }),
          t.addEventListener("click", () => {
            i ? hideTooltip("click") : showTooltip("click");
          }),
          t.addEventListener("focus", () => {
            showTooltip("keyboard");
          }),
          t.addEventListener("blur", () => {
            hideTooltip("keyboard");
          }),
          document.body.addEventListener("keydown", (e) => {
            "Escape" === e.key && hideTooltip("all");
          });
      }, 1);
    }
  }
  customElements.define("tool-tip", ToolTip);
})();
