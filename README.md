# QA_assessment
# WorkFlow Pro — QA Automation Assessment

Submission for the B2B SaaS Platform Testing assessment. Each part is in its own folder with the code and a written explanation of the reasoning behind it.

## Structure

- **[part1_flaky_login](./part1_flaky_login)** — Debugging the flaky login test: identified issues, root causes (CI vs local), and a corrected version with proper waits, 2FA handling, and cleanup. Verified working against a live demo login page.
- **[part2_framework_design](./part2_framework_design)** — Test automation framework design: folder structure, configuration management approach, and open questions about missing requirements (test data, reporting, parallel execution, BrowserStack usage).
- **[part3_integration_test](./part3_integration_test)** — API + UI + mobile integration test for project creation, including tenant isolation verification and cleanup strategy.

## Tools Used
Python, pytest, Playwright, BrowserStack (conceptual integration — see Part 3 explanation for setup assumptions).

## Notes
- `part1_flaky_login/test_login.py` runs successfully against a public demo login page ([the-internet.herokuapp.com](https://the-internet.herokuapp.com/login)), since the assessment's `workflowpro.com` URLs are fictional.
- Parts 2 and 3 are design/reasoning-focused per the assessment's structure; Part 3's code demonstrates the intended logic and structure rather than running against a live backend.
- Assumptions made throughout are called out explicitly in each part's `EXPLANATION.md`.
