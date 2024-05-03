from playwright.sync_api import Page, expect
from axe_playwright_python.sync_playwright import Axe

URLS = [
    "/",
    "/sign-in",
    "/privacy-notice",
    "/accessibility-statement",
    "/support",
    "/documents",
    "/upload",
]

# All available rules/categories are here: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
# Can't include all as gov.uk design system violates the "region" rule
AXE_OPTIONS = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa", "cat.aria", "cat.name-role-value", "cat.structure", "cat.semantics", "cat.text-alternatives", "cat.forms", "cat.sensory-and-visual-cues", "cat.tables", "cat.time-and-media"]}}

axe = Axe()

def test_violations(page: Page):
    for url in URLS:

        page.goto(f"localhost:8090{url}")
        results = axe.run(page, context=None, options=AXE_OPTIONS)
        print(f"\nURL: {url}")
        print(results.generate_report())

        if results.violations_count > 0:
            # Because Python Playwright assertions can't take normal expressions, booleans etc.
            expect(page.get_by_text("Accessibility issues"), f"Accessibility issues at {url}").to_be_visible()
