import "./trusted-types.js";
import "./libs/govuk-frontend.min.js";
import "../../node_modules/i.ai-design-system/dist/iai-design-system.js";

// Because this doesn't appear to be working in Redbox: https://design-system.service.gov.uk/components/button/#stop-users-from-accidentally-sending-information-more-than-once
(() => {
  let buttons = document.querySelectorAll(`[data-prevent-double-click="true"]`);
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      window.setTimeout(() => {
        button.disabled = true;
        window.setTimeout(() => {
          button.disabled = false;
        }, 1000);
      }, 1);
    });
  });
})();
