import logging
from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Any, ClassVar, Union, override

from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Locator, Page, expect
from yarl import URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PageError(ValueError):
    pass


class BasePage(ABC):
    # All available rules/categories can be found at https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
    # Can't include all as gov.uk design system violates the "region" rule
    AXE_OPTIONS: ClassVar[dict[str, Any]] = {
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
        expected_page_title = self.expected_page_title
        expect(self.page).to_have_title(expected_page_title)
        # expect(self.page).to_have_url("url")

    def check_a11y(self, exclude: Sequence[str] | None = None):
        context = {"exclude": exclude} if exclude else None
        expect(self.page.locator(".iai-footer__container")).to_be_visible()  # Ensure page is fully loaded
        results = self.axe.run(self.page, context=context, options=self.AXE_OPTIONS)
        if results.violations_count:
            error_message = f"accessibility violations from page {self}: {results.generate_report()} "
            raise PageError(error_message)

    def navigate_to_privacy_page(self) -> "PrivacyPage":
        self.page.get_by_role("link", name="Privacy", exact=True).click()
        return PrivacyPage(self.page)

    def navigate_to_accessibility_page(self) -> "AccessibilityPage":
        self.page.get_by_role("link", name="Accessibility", exact=True).click()
        return AccessibilityPage(self.page)

    def navigate_to_support_page(self) -> "SupportPage":
        self.page.get_by_role("link", name="Support", exact=True).click()
        return SupportPage(self.page)

    @property
    @abstractmethod
    def expected_page_title(self) -> str: ...

    @property
    def title(self) -> str:
        return self.page.title()

    @property
    def url(self) -> URL:
        return URL(self.page.url)

    def __str__(self) -> str:
        return f'"{self.title}" at {self.url}'


class SignedInBasePage(BasePage, ABC):
    def navigate_to_documents(self) -> "DocumentsPage":
        self.page.get_by_role("link", name="Documents", exact=True).click()
        return DocumentsPage(self.page)

    def navigate_to_chats(self) -> "ChatsPage":
        self.page.get_by_role("link", name="Chats", exact=True).click()
        return ChatsPage(self.page)

    def navigate_my_details(self) -> "MyDetailsPage":
        self.page.get_by_role("link", name="My details", exact=True).click()
        return MyDetailsPage(self.page)

    def sign_out(self) -> "LandingPage":
        self.page.get_by_role("link", name="Chats", exact=True).click()
        return LandingPage(self.page)


class LandingPage(BasePage):
    def __init__(self, page, base_url: URL):
        page.goto(str(base_url))
        super().__init__(page)

    @property
    def expected_page_title(self) -> str:
        return "Redbox"

    def navigate_to_sign_in(self) -> "SignInPage":
        self.page.get_by_role("link", name="Sign in", exact=True).click()
        return SignInPage(self.page)


class SignInPage(BasePage):
    @property
    def expected_page_title(self) -> str:
        return "Sign in - Redbox"

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
    @property
    def expected_page_title(self) -> str:
        return "Sign in - link sent - Redbox"


class SignInConfirmationPage(BasePage):
    EXPECTED_TITLE = "Sign in - confirmation - Redbox"

    def __init__(self, page, magic_link: URL):
        page.goto(str(magic_link))
        super().__init__(page)

    @property
    def expected_page_title(self) -> str:
        return SignInConfirmationPage.EXPECTED_TITLE

    def start(self) -> Union["DocumentsPage", "MyDetailsPage"]:
        self.page.get_by_role("button", name="Start", exact=True).click()
        logger.debug("sign in confirmation navigating to %s", self)
        return self._where_are_we(self.page)

    @staticmethod
    def autosubmit(page: Page, magic_link: URL) -> Union["ChatsPage", "MyDetailsPage"]:
        page.goto(str(magic_link))
        expect(page).not_to_have_title(SignInConfirmationPage.EXPECTED_TITLE)
        return SignInConfirmationPage._where_are_we(page)

    @staticmethod
    def _where_are_we(page: Page) -> Union["ChatsPage", "MyDetailsPage"]:
        return MyDetailsPage(page) if page.title().startswith("My details") else ChatsPage(page)


class HomePage(SignedInBasePage):
    @property
    def expected_page_title(self) -> str:
        return "Redbox"


class MyDetailsPage(SignedInBasePage):
    @property
    def expected_page_title(self) -> str:
        return "My details - Redbox"

    @property
    def name(self) -> str:
        return self.page.get_by_label("Full Name").get_by_role(role="option", selected=True).input_value()

    @name.setter
    def name(self, name: str):
        self.page.get_by_label("Full Name").fill(name)

    def ai_experience(self, ai_experience: str):
        self.page.get_by_test_id(ai_experience).click()

    ai_experience = property(fset=ai_experience)

    @property
    def grade(self) -> str:
        return self.page.get_by_label("Grade").get_by_role(role="option", selected=True).inner_text()

    @grade.setter
    def grade(self, grade: str):
        self.page.get_by_label("Grade").select_option(grade)

    @property
    def business_unit(self) -> str:
        return self.page.get_by_label("Business unit").get_by_role(role="option", selected=True).inner_text()

    @business_unit.setter
    def business_unit(self, grade: str):
        self.page.get_by_label("Business unit").select_option(grade)

    @property
    def profession(self) -> str:
        return self.page.get_by_label("Profession").get_by_role(role="option", selected=True).inner_text()

    @profession.setter
    def profession(self, grade: str):
        self.page.get_by_label("Profession").select_option(grade)

    def update(self) -> "ChatsPage":
        self.page.get_by_text("Update").click()
        return ChatsPage(self.page)


@dataclass
class DocumentRow:
    filename: str
    status: str
    completed: bool


class DocumentsPage(SignedInBasePage):
    @property
    def expected_page_title(self) -> str:
        return "Documents - Redbox"

    def navigate_to_upload(self) -> "DocumentUploadPage":
        self.page.get_by_role("button", name="Add document").click()
        return DocumentUploadPage(self.page)

    def delete_latest_document(self) -> "DocumentDeletePage":
        self.page.get_by_role("button", name="Delete").first.click()
        return DocumentDeletePage(self.page)

    @property
    def all_documents(self) -> list[DocumentRow]:
        return [self._doc_from_element(element) for element in self.page.locator(".iai-doc-list__item").all()]

    @staticmethod
    def _doc_from_element(element: Locator) -> DocumentRow:
        filename = element.locator(".iai-doc-list__cell--file-name").inner_text()
        status = element.locator(".iai-doc-list__cell--status").inner_text()
        completed = element.evaluate(
            "element => element.closest('.iai-doc-list').classList.contains('iai-doc-list--complete')"
        )
        return DocumentRow(filename=filename, status=status, completed=completed)

    def document_count(self) -> int:
        return len(self.all_documents)

    def wait_for_documents_to_complete(self, retry_interval: int = 5, max_tries: int = 120):
        tries = 0
        while True:
            if all(d.completed for d in self.all_documents):
                return
            if tries >= max_tries:
                logger.error("documents: %s", self.all_documents)
                error_message = "Too many retries waiting documents to complete"
                raise PageError(error_message)
            tries += 1
            sleep(retry_interval)


class DocumentUploadPage(SignedInBasePage):
    @property
    def expected_page_title(self) -> str:
        return "Upload a document - Redbox"

    def upload_documents(self, upload_files: Sequence[Path]) -> DocumentsPage:
        self.get_file_chooser_by_label().set_files(upload_files)
        self.page.get_by_role("button", name="Upload").click()
        return DocumentsPage(self.page)

    def get_file_chooser_by_label(self):
        with self.page.expect_file_chooser() as fc_info:
            self.page.get_by_label("Upload a document").click()
        return fc_info.value


class DocumentDeletePage(SignedInBasePage):
    @property
    def expected_page_title(self) -> str:
        return "Remove document - Redbox"

    def confirm_deletion(self) -> "DocumentsPage":
        self.page.get_by_role("button", name="Remove").click()
        return DocumentsPage(self.page)


@dataclass
class ChatMessage:
    status: str | None
    role: str
    route: str | None
    text: str
    sources: Sequence[str]
    element: Locator = field(repr=False)
    chats_page: "ChatsPage" = field(repr=False)

    def navigate_to_citations(self) -> "CitationsPage":
        self.element.locator("a.iai-chat-bubble__citations-button").click()
        return CitationsPage(self.chats_page.page)

    @classmethod
    def from_element(cls, element: Locator, page: "ChatsPage") -> "ChatMessage":
        status = element.get_attribute("data-status")
        role = element.locator(".iai-chat-bubble__role").inner_text()
        route = element.locator(".iai-chat-bubble__route-text").inner_text() or None
        text = element.locator(".iai-chat-bubble__text").inner_text()
        sources = element.locator("sources-list").get_by_role("listitem").all_inner_texts()
        return cls(status=status, role=role, route=route, text=text, sources=sources, element=element, chats_page=page)


class ChatsPage(SignedInBasePage):
    @override
    def check_a11y(self, **kwargs):
        # Exclude AI generated content, since we can't control it.
        return super().check_a11y(exclude=[".iai-chat-bubble__text"])

    @property
    def expected_page_title(self) -> str:
        return "Chats - Redbox"

    @property
    def write_message(self) -> str:
        return self.page.locator("#message").input_value()

    @write_message.setter
    def write_message(self, value: str):
        self.page.locator("#message").fill(value)

    @property
    def available_file_names(self) -> Sequence[str]:
        return self.page.locator("document-selector .govuk-checkboxes__label").all_inner_texts()

    @property
    def selected_file_names(self) -> Collection[str]:
        return {file_name for file_name in self.available_file_names if self.page.get_by_label(file_name).is_checked()}

    @selected_file_names.setter
    def selected_file_names(self, file_names_to_select: Collection[str]):
        for file_name in self.available_file_names:
            checkbox = self.page.get_by_label(file_name)
            if file_name in file_names_to_select:
                checkbox.check()
            else:
                checkbox.uncheck()

    def feedback_stars(self, rating: int):
        self.page.locator(".feedback__container").get_by_role("button").nth(rating - 1).click()

    feedback_stars = property(fset=feedback_stars)

    @property
    def feedback_text(self) -> str:
        return self.page.locator(".feedback__container").get_by_role("textbox").inner_text()

    @feedback_text.setter
    def feedback_text(self, text: str):
        self.page.locator(".feedback__container").get_by_role("textbox").fill(text)

    def feedback_chips(self, chips: Collection[str]):
        for chip in chips:
            self.page.locator(".feedback__container").get_by_test_id(chip).check()

    feedback_chips = property(fset=feedback_chips)

    @property
    def chat_title(self) -> str:
        return self.page.locator(".chat-title__heading").inner_text()

    @chat_title.setter
    def chat_title(self, title: str):
        self.page.locator(".chat-title__edit-btn").click()
        input_ = self.page.get_by_label("Chat Title")
        input_.fill(title)
        input_.press("Enter")

    def start_new_chat(self) -> "ChatsPage":
        self.page.get_by_role("button", name="New chat").click()
        return ChatsPage(self.page)

    def send(self) -> "ChatsPage":
        self.page.get_by_text("Send").click()
        return ChatsPage(self.page)

    def improve(self):
        self.page.get_by_role("button", name="Help improve the response").click()

    def submit_feedback(self):
        self.page.locator(".feedback__container").get_by_role("button", name="Submit").click()

    @property
    def all_messages(self) -> Sequence[ChatMessage]:
        return [ChatMessage.from_element(element, self) for element in self.page.locator("chat-message").all()]

    def get_all_messages_once_streaming_has_completed(
        self, retry_interval: int = 1, max_tries: int = 120
    ) -> Sequence[ChatMessage]:
        tries = 0
        while True:
            messages = self.all_messages
            if not any(m.status == "streaming" for m in messages):
                logger.info("messages: %s", messages)
                return messages
            if tries >= max_tries:
                logger.error("messages: %s", messages)
                error_message = "Too many retries waiting for response"
                raise PageError(error_message)
            tries += 1
            sleep(retry_interval)

    def wait_for_latest_message(self, role="Redbox") -> ChatMessage:
        return [m for m in self.get_all_messages_once_streaming_has_completed() if m.role == role][-1]

    def navigate_to_titled_chat(self, title: str) -> "ChatsPage":
        self.page.get_by_role("link", name=title).click()
        return ChatsPage(self.page)


class CitationsPage(SignedInBasePage):
    @override
    def check_a11y(self, **kwargs):
        # Exclude AI generated content, since we can't control it.
        return super().check_a11y(exclude=[".iai-chat-bubble__text"])

    @property
    def expected_page_title(self) -> str:
        return "Citations - Redbox"

    def back_to_chat(self) -> ChatsPage:
        self.page.get_by_role("link", name="Back to chat", exact=True).click()
        return ChatsPage(self.page)


class PrivacyPage(BasePage):
    @property
    def expected_page_title(self) -> str:
        return "Privacy notice - Redbox"


class AccessibilityPage(BasePage):
    @property
    def expected_page_title(self) -> str:
        return "Accessibility statement - Redbox"


class SupportPage(BasePage):
    @property
    def expected_page_title(self) -> str:
        return "Support - Redbox"
