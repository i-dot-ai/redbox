from playwright.sync_api import Page, expect

def test_has_title(page: Page):
    page.goto("http://localhost:8090/")
    expect(page.get_by_text("Redbox Copilot")).to_be_visible()
