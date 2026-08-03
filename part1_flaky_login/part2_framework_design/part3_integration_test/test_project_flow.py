import os
import pytest
import requests
from playwright.sync_api import sync_playwright, expect

# ---------------------------------------------------------------------------
# CONFIG / TEST DATA
# ---------------------------------------------------------------------------
# Assumptions (since the spec doesn't state these):
# - Base API/UI URLs and auth tokens come from environment variables, not
#   hardcoded, so this can run against any environment (local/staging/CI).
# - Each tenant has its own subdomain (company1.workflowpro.com) and its own
#   API token/tenant ID, matching the framework design from Part 2.
# - Test data (project name) is uniquely generated per run to avoid
#   collisions when tests run in parallel.

import uuid

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.workflowpro.com/v1")
WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "https://company1.workflowpro.com")
AUTH_TOKEN = os.environ["TEST_API_TOKEN"]
TENANT_ID = os.environ.get("TEST_TENANT_ID", "company1")
OTHER_TENANT_ID = os.environ.get("TEST_OTHER_TENANT_ID", "company2")

UNIQUE_PROJECT_NAME = f"Automation Test Project {uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# STEP 1: API — Create the project
# ---------------------------------------------------------------------------
def create_project_via_api():
    """Creates a project through the API and returns the response JSON.
    Using the API (not the UI) to set up test state is faster and more
    reliable than clicking through the UI just to get to a starting point."""
    response = requests.post(
        f"{API_BASE_URL}/projects",
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "X-Tenant-ID": TENANT_ID,
        },
        json={
            "name": UNIQUE_PROJECT_NAME,
            "description": "Created by automated integration test",
            "team_members": [],
        },
        timeout=10,
    )
    assert response.status_code in (200, 201), (
        f"Project creation failed: {response.status_code} {response.text}"
    )
    return response.json()


# ---------------------------------------------------------------------------
# STEP 2: Web UI — Verify project appears
# ---------------------------------------------------------------------------
def verify_project_in_web_ui(project_name: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(f"{WEB_BASE_URL}/login")
            page.fill("#email", os.environ["TEST_USER_EMAIL"])
            page.fill("#password", os.environ["TEST_USER_PASSWORD"])
            page.click("#login-btn")
            page.wait_for_url("**/dashboard**")

            page.goto(f"{WEB_BASE_URL}/projects")

            # expect() retries until the project card renders, handling
            # dynamic loading instead of asserting instantly
            project_card = page.locator(".project-card", has_text=project_name)
            expect(project_card).to_be_visible(timeout=10000)
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# STEP 3: Mobile — Check accessibility via BrowserStack
# ---------------------------------------------------------------------------
def verify_project_on_mobile(project_name: str):
    """
    Assumption: BrowserStack is used via its WebDriver/Playwright endpoint,
    connecting to a real device in the cloud rather than a local emulator.
    Capabilities (device, OS version) would normally come from the
    browsers.yaml config described in Part 2, not hardcoded here.
    """
    bstack_capabilities = {
        "browser": "chrome",
        "device": "Samsung Galaxy S23",
        "os_version": "13.0",
        "project": "WorkFlow Pro Integration Tests",
        "build": "project-creation-flow",
    }
    ws_endpoint = (
        f"wss://cdp.browserstack.com/playwright?caps="
        f"{os.environ['BROWSERSTACK_CAPS_ENCODED']}"
    )

    with sync_playwright() as p:
        browser = p.chromium.connect(ws_endpoint)
        page = browser.new_page()
        try:
            page.goto(f"{WEB_BASE_URL}/login")
            page.fill("#email", os.environ["TEST_USER_EMAIL"])
            page.fill("#password", os.environ["TEST_USER_PASSWORD"])
            page.click("#login-btn")
            page.wait_for_url("**/dashboard**")

            page.goto(f"{WEB_BASE_URL}/projects")
            project_card = page.locator(".project-card", has_text=project_name)
            expect(project_card).to_be_visible(timeout=15000)  # mobile networks are slower
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# STEP 4: Security — Verify tenant isolation
# ---------------------------------------------------------------------------
def verify_tenant_isolation(project_id: str):
    """A user from a DIFFERENT tenant should NOT be able to see or fetch
    this project, either via API or UI. This checks the API boundary
    directly, which is the most reliable way to test authorization logic."""
    response = requests.get(
        f"{API_BASE_URL}/projects/{project_id}",
        headers={
            "Authorization": f"Bearer {os.environ['TEST_OTHER_TENANT_API_TOKEN']}",
            "X-Tenant-ID": OTHER_TENANT_ID,
        },
        timeout=10,
    )
    # Expect 403 (Forbidden) or 404 (Not Found) - either is an acceptable
    # way to enforce isolation, but 200 would be a serious security bug.
    assert response.status_code in (403, 404), (
        f"SECURITY ISSUE: other-tenant user could access project. "
        f"Status: {response.status_code}"
    )


# ---------------------------------------------------------------------------
# THE INTEGRATION TEST
# ---------------------------------------------------------------------------
def test_project_creation_flow():
    # 1. API: Create project
    project = create_project_via_api()
    project_name = project["name"]
    project_id = project["id"]

    # 2. Web UI: Verify project display
    verify_project_in_web_ui(project_name)

    # 3. Mobile: Check mobile accessibility
    verify_project_on_mobile(project_name)

    # 4. Security: Verify tenant isolation
    verify_tenant_isolation(project_id)

    # Cleanup: remove the project so repeated runs don't pollute the tenant
    cleanup_response = requests.delete(
        f"{API_BASE_URL}/projects/{project_id}",
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "X-Tenant-ID": TENANT_ID,
        },
        timeout=10,
    )
    assert cleanup_response.status_code in (200, 204)