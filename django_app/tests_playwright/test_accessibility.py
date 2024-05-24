import logging

from _settings import BASE_URL
from _signin import sign_in
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)
URLS = ["", "sign-in", "privacy-notice", "accessibility-statement", "support", "documents", "upload", "chats"]

# All available rules/categories are here: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
# Can't include all as gov.uk design system violates the "region" rule
AXE_OPTIONS = {
    "runOnly": {
        "type": "tag",
        "values": [
            "wcag2a",
            "wcag2aa",
            "wcag21aa",
            "wcag22aa",
            "cat.aria",
            "cat.name-role-value",
            "cat.structure",
            "cat.semantics",
            "cat.text-alternatives",
            "cat.forms",
            "cat.sensory-and-visual-cues",
            "cat.tables",
            "cat.time-and-media",
        ],
    }
}

axe = Axe()


def test_violations(page: Page):
    sign_in(page)

    for url in URLS:
        page.goto(f"{BASE_URL / url}")
        results = axe.run(page, context=None, options=AXE_OPTIONS)
        logger.debug("\nURL: %s", url)
        logger.info(results.generate_report())

        if results.violations_count > 0:
            # Because Python Playwright assertions can't take normal expressions, booleans etc.
            expect(page.get_by_text("Accessibility issues"), f"Accessibility issues at {url}").to_be_visible()
