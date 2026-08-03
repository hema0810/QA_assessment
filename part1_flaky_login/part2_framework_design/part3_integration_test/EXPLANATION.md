# Part 3: API + UI + Mobile Integration Test — Approach

## Test Data Management
- The project name is generated with a unique suffix (`uuid.uuid4().hex[:8]`) on every run, so parallel test runs or repeated CI runs never collide on the same name within a tenant.
- The project is created via **API**, not by clicking through the UI. This is faster, more reliable (fewer moving parts to fail), and keeps the test focused on what it's actually verifying — that data created one way is visible another way.
- Cleanup happens at the end via a DELETE call, so the tenant's project list doesn't accumulate test data over time. If the test fails partway through, this cleanup step is a known gap — in a real framework, I'd move this into a pytest fixture's teardown (using `yield`) so it always runs, not just on the happy path.

## Cross-Platform Validation
- Web UI is tested with a standard local Playwright browser launch.
- Mobile is tested by connecting Playwright to a **real device in BrowserStack's cloud** via its WebSocket endpoint, rather than emulating a mobile viewport locally — this catches real device rendering issues that a resized desktop browser window would miss.
- Both web and mobile checks reuse the same underlying assertion pattern (`expect(locator).to_be_visible()`), so the test logic stays consistent even though the execution environment differs.
- In a full framework, this test would be parametrized to run across the full device/browser matrix defined in the `browsers.yaml` config from Part 2, rather than hardcoding one device as done here for clarity.

## Tenant Isolation / Security
- Checked directly at the **API level** with a second tenant's credentials attempting to fetch the first tenant's project.
- Expects a `403` or `404` — either is an acceptable way to enforce the boundary, but a `200` response would indicate a serious cross-tenant data leak.
- Testing this at the API layer (rather than only checking "the UI doesn't show it") is important: a UI might simply filter what it displays while the backend endpoint remains unprotected, which is a real vulnerability a UI-only test wouldn't catch.

## Edge Cases Considered
- **Network failures**: All HTTP calls have explicit `timeout` values so a hung request fails the test clearly instead of hanging CI indefinitely.
- **Slow loading**: UI checks use `expect().to_be_visible(timeout=...)` with auto-retry rather than one-shot checks; the mobile check uses a longer timeout (15s vs 10s) since mobile network conditions in BrowserStack's cloud devices are typically slower and more variable than desktop.
- **Mobile responsiveness**: handled by testing on an actual BrowserStack device rather than assuming desktop CSS breakpoints behave the same on real mobile browsers.

## Assumptions Made
- Authentication uses a bearer token per tenant, obtained separately (not shown — would come from a login/token fixture).
- BrowserStack capabilities and connection details would normally be pulled from the `browsers.yaml` config in Part 2, not hardcoded — simplified here for readability.
- The API returns `200`/`201` for successful creation and `200`/`204` for successful deletion; exact codes would need confirming with the backend team.

## What I'd Ask the Team
- What's the actual auth flow for API tests — service account tokens, or the same user login token reused across API and UI calls?
- Should tenant-isolation tests also check the **web UI directly** (e.g., attempt to load the other tenant's project URL while logged in as a different tenant's user), in addition to the API-level check?
- Is there a sandbox/throwaway tenant specifically for automation, so cleanup failures don't risk polluting a tenant other teams also test against?