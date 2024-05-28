from playwright.sync_api import Page
from tests_playwright.pages import LandingPage


def test_support_pages(page: Page):

    # Landing page
    landing_page = LandingPage(page)
    
    # Privacy page
    privacy_page = landing_page.navigate_to_privacy_page()

    # Accessibility page
    accessibility_page = landing_page.navigate_to_accessibility_page()

    # Support page
    support_page = landing_page.navigate_to_support_page()
