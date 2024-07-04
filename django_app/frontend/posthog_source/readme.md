# Posthog setup

These instructions are based on the docs at https://posthog.com/docs/libraries/js#advanced-option---bundle-all-required-extensions

After making changes to index.js, run from this folder:

`npx parcel build index.html`

That will create a `JS` file in the `/frontend/dist/` folder. Copy this file to `/frontend/js/posthog.js`. You can then delete the contents of the `/frontend/dist/` folder.
