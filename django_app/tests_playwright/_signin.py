import os
import subprocess
from playwright.sync_api import Page, expect

def sign_in(page: Page):

    print("Signing in")

    email_address = os.environ["USER_EMAIL"]

    # Sign in page
    page.goto("http://localhost:8090/sign-in/")
    expect(page.get_by_text("Redbox Copilot")).to_be_visible()
    page.get_by_label("Email Address").type(email_address)
    page.get_by_text("Continue").click()

    # Get magic link
    os.chdir('..')
    command = ["poetry", "run", "python", "manage.py", "show_magiclink_url", email_address]
    result = subprocess.run(command, capture_output=True, text=True)
    magic_link = result.stdout.strip()
    
    # Complete sign-in and verify
    page.goto(f"http://localhost:8090{magic_link}")
    page.get_by_role("button").click()
    expect(page.get_by_text("Sign out")).to_be_visible()
