import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path

from _settings import BASE_URL
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page, expect
from yarl import URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        # expect(self.page).to_have_url("url")

    def check_a11y(self):
        results = self.axe.run(self.page, context=None, options=self.AXE_OPTIONS)
        if results.violations_count > 0:
            expect(
                self.page.get_by_text("Accessibility issues"),
                f"Accessibility issues in {self.__class__.__name__} at {self.url}",
            ).to_be_visible()

    @abstractmethod
    def get_expected_page_title(self) -> str: ...

    @property
    def title(self) -> str:
        return self.page.title()

    @property
    def url(self) -> URL:
        return URL(self.page.url)

    def __str__(self) -> str:
        return f'"{self.title}" at {self.url}'


class SignedInBasePage(BasePage, metaclass=ABCMeta):
    def navigate_to_documents(self) -> "DocumentsPage":
        self.page.get_by_role("link", name="Documents", exact=True).click()
        return DocumentsPage(self.page)

    def navigate_to_chats(self) -> "ChatsPage":
        self.page.get_by_role("link", name="Chats", exact=True).click()
        return ChatsPage(self.page)

    def sign_out(self) -> "LandingPage":
        self.page.get_by_role("link", name="Chats", exact=True).click()
        return LandingPage(self.page)


class LandingPage(BasePage):
    def __init__(self, page):
        page.goto(str(BASE_URL))
        super().__init__(page)

    def get_expected_page_title(self) -> str:
        return "Redbox Copilot"

    def navigate_to_sign_in(self) -> "SignInPage":
        self.page.get_by_role("link", name="Sign in", exact=True).click()
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

    def continue_(self) -> "SignInLinkSentPage":
        self.page.get_by_text("Continue").click()
        return SignInLinkSentPage(self.page)


class SignInLinkSentPage(BasePage):
    def get_expected_page_title(self) -> str:
        return "Sign in - link sent - Redbox Copilot"


class SignInConfirmationPage(BasePage):
    def __init__(self, page, magic_link: URL):
        page.goto(str(magic_link))
        super().__init__(page)

    def get_expected_page_title(self) -> str:
        return "Sign in - confirmation - Redbox Copilot"

    def navigate_to_home_page(self) -> "HomePage":
        self.page.get_by_role("button", name="Sign in", exact=True).click()
        return HomePage(self.page)


class HomePage(SignedInBasePage):
    def get_expected_page_title(self) -> str:
        return "Redbox Copilot"


class DocumentsPage(SignedInBasePage):
    def get_expected_page_title(self) -> str:
        return "Documents - Redbox Copilot"

    def navigate_to_upload(self) -> "DocumentUploadPage":
        self.page.get_by_role("button", name="Upload a new document").click()
        return DocumentUploadPage(self.page)

    def should_contain_file_named(self, file_name: str):
        expect(self.page.get_by_role("cell", name=file_name, exact=True)).to_be_visible()


class DocumentUploadPage(SignedInBasePage):
    def get_expected_page_title(self) -> str:
        return "Upload a document - Redbox Copilot"

    def upload_document(self, upload_file: Path) -> DocumentsPage:
        self.get_file_chooser_by_label().set_files(upload_file)
        self.page.get_by_role("button", name="Upload").click()
        return self.navigate_to_documents()

    def get_file_chooser_by_label(self):
        with self.page.expect_file_chooser() as fc_info:
            self.page.get_by_label("Upload a document").click()
        return fc_info.value


class ChatsPage(SignedInBasePage):
    def get_expected_page_title(self) -> str:
        return "Chats - Redbox Copilot"

    @property
    def write_message(self) -> str:
        return self.page.locator("#message").input_value()

    @write_message.setter
    def write_message(self, value: str):
        self.page.locator("#message").fill(value)

    def send(self) -> "ChatsPage":
        self.page.get_by_text("Send").click()
        return ChatsPage(self.page)

    def all_messages(self) -> list[str]:
        return self.page.locator(".iai-chat-message").all_inner_texts()
