from abc import ABCMeta, abstractmethod

from _settings import BASE_URL
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Locator, Page, expect


class BasePage(metaclass=ABCMeta):
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

    def __init__(self, page: Page):
        self.page = page
        self.axe = Axe()
        self.check_title()
        self.check_a11y()

    def check_title(self):
        expected_page_title = self.get_expected_page_title()
        expect(self.page).to_have_title(expected_page_title)

    def check_a11y(self):
        results = self.axe.run(self.page, context=None, options=self.AXE_OPTIONS)
        if results.violations_count > 0:
            expect(
                self.page.get_by_text("Accessibility issues"),
                f"Accessibility issues in {self.__class__.__name__} at {self.page.url}",
            ).to_be_visible()

    @abstractmethod
    def get_expected_page_title(self) -> str: ...


class HomePage(BasePage):
    def __init__(self, page):
        page.goto(str(BASE_URL))
        super().__init__(page)

    def get_expected_page_title(self) -> str:
        return "Redbox Copilot"

    def sign_in(self) -> "SignInPage":
        sign_in_link: Locator = self.page.get_by_role("link", name="Sign in", exact=True)
        sign_in_link.click()
        return SignInPage(self.page)


class SignInPage(BasePage):
    def get_expected_page_title(self) -> str:
        return "Sign in - Redbox Copilot"

    @property
    def email(self) -> str:
        return self.page.locator("#email").input_value()

    @email.setter
    def email(self, value: str):
        self.page.locator("#email").fill(value)
