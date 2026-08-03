Part 1: Debugging Flaky Test Code
1. Issues Identified

a) No explicit waits after actions that trigger async behavior
The test calls page.click("#login-btn") and immediately asserts the URL changed. Login involves a network request and a redirect, which takes non-zero time. The test doesn't wait for that to complete before checking the result.

b) Exact-match URL assertion

python
assert page.url == "https://app.workflowpro.com/dashboard"

This fails on any variation — trailing slash, query parameters, or an intermediate redirect URL — even when the login actually succeeded.

c) .is_visible() checked as a one-time boolean, not retried

python
assert page.locator(".welcome-message").is_visible()

This checks visibility at that exact instant. If the element hasn't rendered yet (common with dynamically loaded dashboards, per the assessment notes), the check returns False even though the element would appear a moment later.

d) No handling for 2FA
The context notes state some users go through 2FA. The test assumes a direct path from login to dashboard, with no branch for a 2FA prompt.

e) Hardcoded credentials in source code
Credentials are committed directly rather than pulled from environment variables or a secrets manager. This is a maintainability and security issue, and also a reliability risk if the seeded account's password rotates.

f) No cleanup on failure

python
browser.close()

is the last line in the function. If any assert above it fails, the function exits immediately and this line never executes, leaking a browser process. In CI, repeated leaks across a test run can exhaust resources and cause unrelated tests to fail too.

g) No test isolation between runs
Nothing resets state between test executions (e.g., logging out, clearing cookies, or resetting seeded data), so results can depend on what a previous run left behind.

2. Why This Behaves Differently in CI vs Locally
Factor	Local	CI
Machine speed	Fast, dedicated resources	Often slower/shared virtual runners
Network latency	Low (may be a local/staging server)	Higher, more hops
Browser state	Sometimes warm/cached	Always cold start
Parallel execution	Usually one test at a time	Multiple tests/workers running simultaneously, competing for the same tenant/test accounts
Timing margin	Human-paced, generous	Tight; default timeouts get hit more often

The core issue is that all the timing-dependent assertions in the original test have almost no margin for delay. Locally, things usually finish fast enough that the flakiness doesn't surface. In CI, the same code has less headroom, so the race condition between "page finished loading" and "test checks the result" shows up as intermittent failures.

3. Fixes Applied
python
import pytest
import os
from playwright.sync_api import sync_playwright, expect

def test_user_login():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto("https://app.workflowpro.com/login")

            # Credentials from environment, not hardcoded
            page.fill("#email", os.environ["TEST_USER_EMAIL"])
            page.fill("#password", os.environ["TEST_USER_PASSWORD"])
            page.click("#login-btn")

            # Handle optional 2FA step
            two_fa_input = page.locator("#2fa-code")
            if two_fa_input.is_visible(timeout=3000):
                page.fill("#2fa-code", os.environ["TEST_2FA_CODE"])
                page.click("#2fa-submit-btn")

            # Wait for the actual navigation instead of checking instantly
            page.wait_for_url("**/dashboard**")

            # expect() auto-retries until the element appears or times out,
            # instead of checking visibility once
            expect(page.locator(".welcome-message")).to_be_visible()

        finally:
            # Runs even if an assertion above fails, preventing leaked browsers
            browser.close()

What each fix addresses:

page.wait_for_url("**/dashboard**") — waits for actual navigation with a flexible pattern match instead of an exact string, and instead of assuming it already happened.
expect(...).to_be_visible() — Playwright's expect() polls and retries until the condition is true or a timeout is hit, instead of checking once.
2FA branch — checks whether the 2FA element appears within a short timeout; if it does, handles it; if not, proceeds normally. This makes the test resilient to both user types mentioned in the requirements.
Environment variables for credentials — removes hardcoded secrets and makes it easy to swap test accounts per environment (CI vs local vs staging).
try/finally — guarantees browser.close() runs regardless of whether an assertion fails, preventing resource leaks in CI.
