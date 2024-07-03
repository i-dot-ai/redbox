import "../../node_modules/posthog-js/dist/recorder.js";
import "../../node_modules/posthog-js/dist/surveys.js";
import "../../node_modules/posthog-js/dist/exception-autocapture.js";
import "../../node_modules/posthog-js/dist/tracing-headers.js";
import "../../node_modules/posthog-js/dist/web-vitals.js";
import posthog from "posthog-js";

//import "../../node_modules/posthog-js/lib/src/posthog-core.js";
//import "../../node_modules/posthog-js/dist/module.js";
//import "../../node_modules/posthog-js/dist/main.js";

posthog.init("phc_3r2LNsBz7zJFRSpcMmE4PwXEq2m4CwfxJC9H1OeeMJg", {
  api_host: "https://eu.i.posthog.com",
  disable_external_dependency_loading: true, // Optional - will ensure we never try to load extensions lazily
});

export const _frontmatter = {};
