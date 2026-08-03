import pytest
from playwright.sync_api import sync_playwright, expect

def test_user_login():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto("https://the-internet.herokuapp.com/login")
            page.fill("#username", "tomsmith")
            page.fill("#password", "SuperSecretPassword!")
            page.click("button[type='submit']")

            # Wait for the URL to actually change, instead of checking instantly
            page.wait_for_url("**/secure")

            # expect() auto-retries until the element appears, instead of checking once
            expect(page.locator(".flash.success")).to_be_visible()
        finally:
            browser.close()