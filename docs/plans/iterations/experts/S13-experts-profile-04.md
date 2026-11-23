# S13: EXPERTS-PROFILE-04 Keep own-profile account controls authenticated

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S13
acceptance_id: EXPERTS-PROFILE-04
feature_file_path: docs/features/act-18-experts/experts-profile.feature
feature_line: 21
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S10
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 24e18a9b5806e007e79f3e0c4ee01bf775ba5266eab7ccfd7c2d00b472b875cb
```

### A — Context map


| Verified source | Lines | Meaning |
|---|---:|---|
| `docs/features/act-18-experts/experts-profile.feature` | 32–36 | Exact anonymous own-profile redirect and absence contract. |
| `accounts/views.py` | 285–317 | Existing `@login_required` executes before profile logging, token creation and private rendering. |
| `templates/accounts/profile.html` | 5–85 | Existing profile/edit/token controls and stable test IDs. |
| `tests/integration/test_profile_page.py` | 13–58 | Existing coverage checks anonymous 302 and authenticated token/content; anonymous destination and non-disclosure need stronger proof. |
| `docs/architecture/SAO.md` | 2910–2951 | Profile remains auth-only; DRF token stays on authenticated profile. |

Additional inspected sources: replay `AGENTS.md`, `CLAUDE.md`, all three supplied `/tmp` guidance/ownership files, Orient/readiness, SAO Experts delta, IA §11, Cedar JSON, journey own-profile section, AT environment/bindings, E2E configuration/fixtures/helper and graph examples.

### B — Do not do


- Do not remove, bypass or replace existing `@login_required`.
- Do not move token creation or private profile context ahead of authorization.
- Do not turn own-profile into a public Experts route.
- Do not modify production profile code/templates: S10 owns that integration and preservation of account controls.
- Do not recreate Cedar fixtures, numeric projections, stored summaries or HTML parsing.
- Do not duplicate generic Behave phrases: S07 owns Bob anonymous; S03 owns the shared path request; S10 owns Maria authentication/profile opening.
- No account creation for Bob, integration mocks, live provider calls, seed/dev/runtime DB mutations, migrations or permission expansion.
- PIN skeleton bodies remain raising stubs; actual assertions begin after PIN-04 handoff and PIN-05 GO.

### C — Applicable architecture


- **Security & Access Control → FOB**: auth-only profile and Django login redirect.
- **Guest read security**: public Experts access does not grant account/token access.
- **Experts & Karma delivery architecture → Web delivery and notification reuse**: extend existing own-profile route and retain editing.
- **Experts & Karma delivery architecture → Test strategy**: real DB/client AT and separate Playwright certification.
- **IA §11 → Exact display contract**: stable profile hooks; account API tokens never public.
- **User journey → Screen FOB-PROFILE-VIEW-1**: Bob redirects to sign-in.

Implementation approach: certify existing guard after S10 adds contributions. No new service, view, decorator or production helper is necessary.

### D — Tests and exact assertions


| Test/binding | Required assertions |
|---|---|
| `test_own_profile_with_anonymous_request_redirects_without_private_render` | Real anonymous GET returns exactly 302; parsed Location path equals `reverse("login")`; parsed `next` equals `/auth/user/profile/`; profile template is not rendered; no profile controls/Karma nodes in redirect body; no private token appears; token rows unchanged; no `[PROFILE] Page GET` or `[PROFILE] Render` records. |
| `test_own_profile_with_followed_anonymous_redirect_shows_login_only` | Fresh anonymous client follows exactly one expected login redirect; final 200 contains `login-form`; excludes own-profile controls/Karma/summary and Maria's actual test token; authenticated session key absent; token rows unchanged. |
| AT `he is redirected to the login page` | Inspect unfollowed `context.response`: status, exact login destination and `next`; require prior request was own-profile. |
| AT `no own-profile Karma or account token controls are shown` | Check original response and a separately followed login GET; login form exists only on destination; exclude all private control IDs and stored token keys; no token/account creation. |
| `test_own_profile_with_anonymous_browser_navigation_shows_login_only` | Fresh browser context navigates directly to own-profile; browser ends on login with correct `next`; `login-form` visible; all own-profile IDs absent from DOM; no authenticated session established. |

Private ID set: `profile-page`, `profile-edit-btn`, `profile-karma-card`, `profile-karma-total`, `profile-contribution-summary`, `profile-token-field`, `profile-token-toggle`, `profile-token-copy`, `profile-token-regenerate-form`, `profile-token-regenerate-password`, `profile-token-regenerate-submit`.

Use real `load_cedar_baseline()` from S03 and create/retrieve Maria’s real test DRF token before request to make secret non-disclosure meaningful. Bob has no User row. Snapshot token rows after setup and before request.

Reuse `tests/support/experts_html.py` helpers, especially `find_by_test_id`; do not introduce a parser. Existing authenticated profile/token rotation tests remain regression gates. S10 owns the new authenticated profile control assertion.

Commands:

```sh
pytest tests/integration/test_experts_profile_auth.py tests/integration/test_profile_page.py -x
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^EXPERTS-PROFILE-04 Keep own-profile account controls authenticated$' docs/features/act-18-experts/experts-profile.feature
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_auth.py -x
make test-at-harness
```

The explicit `--tags=@experts` overrides configured `not @wip` selection for this exact contract. Require one executed scenario/four successful steps; zero, undefined or skipped steps fail completion. Aggregate `make test-at-experts` remains a later whole-feature gate.

### E — Log story


Not applicable: this slice adds no production controller/service action or branch. Existing Django authentication rejects the request before `profile_view` runs. Adding an artificial rejection controller solely to emit logs would duplicate established authorization.

The first integration test captures logs and proves absence of the existing private profile entry/render messages on rejection. This is a non-execution assertion, not a fabricated log story. No `log_story_script`, `log_tests` or `log_story_command`.

### F — MCP tools


Not applicable. This contract exercises a session-authenticated web route and HTML. No MCP/API registration, facade client, tool schema or auth forwarding changes.

### G — Agent proofs


Not applicable. No agent capability, model call or summary generation occurs during anonymous own-profile rejection. SAO §17 remains unchanged; no ScriptedLLM, trace scripts, ToolExecutor or PRF added.

### H — Mockup graduation and delivery


`templates/mockups/experts/own_profile.html` is a design reference for S10. Production destination remains `templates/accounts/profile.html`, owned by S10. S13 certifies that anonymous users never reach it. It does not copy a mockup or produce a public duplicate of account controls.

Proposed implementation footprint:



No worker writes occurred; actual footprint and skeleton SHA belong to sequential PIN application.



Complete skeleton text follows. All paths are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`; all modes are **create**. Existing production behavior is untouched.

`tests/integration/test_experts_profile_auth.py`:

```python
"""EXPERTS-PROFILE-04 real-client authorization certification."""

import pytest
from django.test import Client
from _pytest.logging import LogCaptureFixture

from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_html import find_by_test_id


@pytest.mark.django_db
def test_own_profile_with_anonymous_request_redirects_without_private_render(
    client: Client, caplog: LogCaptureFixture
) -> None:
    """Prove authorization precedes private rendering and token access.

    :param client: Anonymous real Django client. Example: Client().
    :param caplog: Pytest log capture. Example: INFO capture for accounts.views.
    :return: None. Example: None after assertions pass.
    :raises AssertionError: For a wrong redirect, disclosure or token mutation.
    """
    # Load Cedar; prepare Maria token; snapshot rows; GET without following.
    # Assert exact login/next, absent private nodes/secrets and profile logs.
    raise NotImplementedError()


@pytest.mark.django_db
def test_own_profile_with_followed_anonymous_redirect_shows_login_only(
    client: Client,
) -> None:
    """Prove the redirect destination presents only anonymous login controls.

    :param client: Anonymous real Django client. Example: Client().
    :return: None. Example: None after assertions pass.
    :raises AssertionError: For extra redirects, private content or session auth.
    """
    # Load Cedar; prepare token; follow GET; inspect chain, DOM and token rows.
    # Reuse shared HTML helper; require login-form and no own-profile controls.
    raise NotImplementedError()
```

`docs/features/steps/experts_profile_auth_steps.py`:

```python
"""Unique S13 assertions; shared actor/request bindings belong elsewhere."""

from behave import then
from behave.runner import Context

from tests.support.experts_html import find_by_test_id


@then("he is redirected to the login page")
def assert_own_profile_login_redirect(context: Context) -> None:
    """Check the unfollowed own-profile response's precise login handoff.

    :param context: Real AT context. Example: context.response.status_code == 302.
    :return: None. Example: None after exact Location/next assertions.
    :raises AssertionError: If profile request, redirect or next differs.
    """
    # Require prior own-profile GET; parse Location and verify login plus next.
    raise NotImplementedError()


@then("no own-profile Karma or account token controls are shown")
def assert_own_profile_controls_absent(context: Context) -> None:
    """Check redirect and login HTML without granting an authenticated session.

    :param context: Real Cedar AT context. Example: context.cedar_dataset.
    :return: None. Example: None after private-control absence assertions.
    :raises AssertionError: If controls, token secrets or an account appear.
    """
    # Preserve original response; snapshot token/account rows; GET destination.
    # Require login-form; reject private IDs/secrets in both bodies; rows stable.
    raise NotImplementedError()
```

`tests/e2e/test_experts_profile_auth.py`:

```python
"""S13 browser certification using the existing isolated fixture lifecycle."""

import pytest
from playwright.sync_api import Page

from tests.support.experts_data import load_cedar_baseline


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_own_profile_with_anonymous_browser_navigation_shows_login_only(
    page: Page, live_server_url: str
) -> None:
    """Prove a fresh anonymous browser cannot display own-profile controls.

    :param page: Existing function-scoped page. Example: fresh Chromium page.
    :param live_server_url: Real test server origin. Example: http://localhost:8001.
    :return: None. Example: None after browser assertions pass.
    :raises AssertionError: For incorrect redirect or exposed private controls.
    """
    # Load Cedar on real test DB; use fresh context without login().
    # Navigate to profile; inspect parsed URL/next and stable test-ID locators.
    raise NotImplementedError()
```

Issue/commit sequence after PIN GO: N1 proof tests → N2 exact AT → N3 browser → N4 evidence/DoD, each with its issue reference and approved issue update; only final completed slice closes the issue. PIN-04/05 owns the combined review.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-profile.feature:21`; 1 expanded case(s), primary layer `at`. Dependencies: S10. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-PROFILE-04
  scenario_dependencies:
  - S10
  nodes:
  - id: S13-N1-profile-auth-proof
    title: Certify existing profile authorization boundary
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_profile_auth.py
    tests:
    - test_own_profile_with_anonymous_request_redirects_without_private_render
    - test_own_profile_with_followed_anonymous_redirect_shows_login_only
    gate:
      command: pytest tests/integration/test_experts_profile_auth.py tests/integration/test_profile_page.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-write-concise-methods
      - do-docstring-format
      - pytest
    notes: Existing behavior is reused; no production code changes.
  - id: S13-N2-exact-at
    title: Bind the two unique rejection assertions
    bpe: BPE-04
    depends_on:
    - S13-N1-profile-auth-proof
    footprint:
    - docs/features/steps/experts_profile_auth_steps.py
    tests:
    - EXPERTS-PROFILE-04
    gate:
      command: make test-experts-s13-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
    notes: Require one executed scenario and four successful steps; reuse S03/S07 bindings.
  - id: S13-N3-browser
    title: Certify anonymous browser redirect and absent controls
    bpe: BPE-05
    depends_on:
    - S13-N2-exact-at
    footprint:
    - tests/e2e/test_experts_profile_auth.py
    tests:
    - test_own_profile_with_anonymous_browser_navigation_shows_login_only
    gate:
      command: make test-experts-s13-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
    notes: Reuse function-scoped page/live_server_url and real Cedar DB; no browser fixture changes.
  - id: S13-N4-dod
    title: Record evidence and verify authorization regression coverage
    bpe: BPE-06
    depends_on:
    - S13-N1-profile-auth-proof
    - S13-N2-exact-at
    - S13-N3-browser
    footprint: []
    gate:
      command: make test-experts-s13
      acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts
        --name='^EXPERTS-PROFILE-04 Keep own-profile account controls authenticated$' docs/features/act-18-experts/experts-profile.feature
      browser_command: E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright
        -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_auth.py -x
      harness_command: make test-at-harness
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-follow-commit-convention
      - do-small-increments
      - do-github-issues
      - pytest
    notes: Record nonzero execution counts and deployed/local identity accurately; no merge/release permission implied.
```

## Lessons Learned

- Existing anonymous profile coverage checks only status 302; exact destination, `next`, absence of token content and absence of token mutation are separate valuable proofs.
- S13 needs no production implementation. Introducing another authorization layer would increase risk and conflict with S10.
- Generic Behave phrase ownership must be explicit: reuse S07/S03 instead of registering locally convenient duplicates.
- Global pytest configuration and feature-level WIP selection can conceal tests; use the scoped commands and require actual execution counts.
- No architecture amendment identified; these assertions enforce the existing SAO contract.

## Structural application evidence

`docs/experts-replay/pin-evidence/S13.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
