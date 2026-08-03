# Part 2: Test Framework Design

## 1. Framework Folder Structure

qa-framework/
├── config/
│ ├── environments.yaml # tenant URLs, per-env settings
│ ├── browsers.yaml # browser/device matrix for BrowserStack
│ └── users.yaml # test user credentials per role (Admin/Manager/Employee), pulled from env vars/secrets
│
├── src/
│ ├── pages/ # Page Object Model - one class per screen
│ │ ├── login_page.py
│ │ ├── dashboard_page.py
│ │ └── project_page.py
│ │
│ ├── api/
│ │ ├── api_client.py # wraps requests/httpx, handles auth headers, tenant headers
│ │ └── endpoints/
│ │ └── projects.py
│ │
│ ├── fixtures/
│ │ ├── browser_fixtures.py # pytest fixtures for browser/context lifecycle (setup + teardown)
│ │ ├── tenant_fixtures.py # parametrized fixtures to run same test across tenants
│ │ └── user_fixtures.py # role-based login fixtures
│ │
│ └── utils/
│ ├── waits.py # custom wait helpers
│ └── data_factory.py # generates test data (project names, users) to avoid collisions
│
├── tests/
│ ├── web/
│ │ ├── test_login.py
│ │ └── test_project_creation.py
│ ├── mobile/
│ │ └── test_mobile_project_view.py
│ ├── api/
│ │ └── test_projects_api.py
│ └── integration/
│ └── test_project_flow_e2e.py
│
├── reports/ # test output, screenshots on failure, videos
├── conftest.py # shared pytest fixtures, hooks
├── pytest.ini # markers, test discovery config
└── requirements.txt


**Key design choices:**
- **Page Object Model (POM)** for the `pages/` layer — keeps selectors and page interactions in one place per screen, so if the UI changes, only one file needs updating instead of every test that touches that screen.
- **Separate `api/` layer** — API tests and the API client used to *set up* UI test state (e.g., creating a project via API before checking it in the UI) share the same client, avoiding duplicate HTTP logic.
- **Fixtures directory separated by concern** (browser, tenant, user) — makes it easy to parametrize tests across multiple tenants or roles without duplicating test logic.

---

## 2. Configuration Management

**Environments:** a YAML/JSON config per environment (`local`, `staging`, `prod-like`) storing base URLs per tenant, e.g.:
```yaml
staging:
  tenants:
    company1: "https://company1-staging.workflowpro.com"
    company2: "https://company2-staging.workflowpro.com"
```
Tests reference tenants by name, not hardcoded URLs, and the active environment is selected via an env variable or `--env` pytest CLI flag.

**Browsers/devices:** a matrix config listing browser + OS + device combos to run against, consumed by both local Playwright runs and BrowserStack sessions — so the same test suite can target either backend by swapping a config flag, not rewriting tests.

**Test data:** a data factory pattern (`utils/data_factory.py`) generates uniquely-named test entities (e.g., `f"Test Project {uuid4()}"`) so parallel test runs don't collide on the same project/user name within a tenant.

**Secrets:** credentials, API tokens, and BrowserStack keys are never hardcoded — pulled from environment variables, populated via CI secrets manager (e.g., GitHub Actions secrets) locally via a `.env` file that's gitignored.

---

## 3. Missing Requirements — Questions I'd Ask

**Test data management:**
- Is there a dedicated staging/QA tenant environment, or do automated tests run against shared data used by other teams?
- Should test-created projects be cleaned up after each run (via API teardown), or is there a nightly reset?
- Are there pre-seeded accounts per role, or does the framework need to create/provision them?

**Reporting:**
- What's the expected reporting output — Allure, HTML report, integration with a dashboard (e.g., TestRail, Slack notifications on failure)?
- Do failures need to auto-capture screenshots/video/traces (Playwright supports this out of the box) for debugging without re-running?

**Parallel execution:**
- Can tests run in parallel safely, or do some (e.g., tenant-level settings changes) need to run serially to avoid state conflicts?
- What's the target CI run time, since that affects how aggressively to parallelize and how many BrowserStack sessions to provision concurrently?

**BrowserStack specifics:**
- Is there an existing BrowserStack account/budget, or does usage need to be optimized for cost (e.g., only running the full device matrix on merge to main, and a smaller smoke-test matrix on every PR)?
- Are there specific real devices required (per real user analytics), or is a standard matrix (e.g., latest 2 versions of Chrome/Safari, one Android, one iOS) sufficient?

**Ownership/maintenance:**
- Who maintains selectors when the frontend team changes UI — is there a contract (e.g., `data-testid` attributes) the frontend team commits to keeping stable for test automation?
- What's the versioning/release cadence, so tests can be tied to specific app versions if needed?