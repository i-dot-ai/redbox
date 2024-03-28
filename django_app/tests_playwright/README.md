# Automated Accessibility Testing using Playwright and Axe

The tests are currently located at `django_app/tests_playwright`. All commands below should be run from this directory.

## Setup

`poetry run playwright install`

## Running tests

From `django_app/tests_playwright` directory:

`poetry run pytest -s`

Commandline options are documented at https://playwright.dev/python/docs/running-tests
