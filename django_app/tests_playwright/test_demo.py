from _settings import BASE_URL
from playwright.sync_api import Page, expect


def test_has_title(page: Page):
    page.goto(BASE_URL)
    expect(page.get_by_text("Redbox Copilot")).to_be_visible()
