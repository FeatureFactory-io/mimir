# Experts verification assets and gaps

The Cedar job, living feature files, mockups and operator script share
`test-data/experts/cedar-rfp-01.json`. Reset independent event cases. Restore the
baseline before UAT; do not combine the before/after numbers from separate cases.

## Existing assets to reuse

- AT integration patterns: `tests/integration/test_guest_playbook_browse.py`,
  `test_api_public_playbook_access.py`, `test_profile_edit_email_change.py` and
  PIP decision tests. These use the Django client and real database objects.
- Existing fixture data: `tests/fixtures/e2e_seed.json`, `journey_seed.json` and
  `playbooks_seed.json`. Reuse their construction patterns, not their numeric IDs
  or private users as the Cedar truth set.
- E2E specification: `tests/e2e/experts-journey.feature` contains the three Cedar journeys and responsive outlines. It is separate from Django-client AT.
- E2E helpers: `tests/e2e/e2e_helpers.py` supplies `login`; conftest supplies a
  fresh browser context, a real Django live server and fixture setup. Keep AT
  and Playwright step implementations separate.
- UAT operator vocabulary: `tests/uat/e2e-uat-flow.feature` already uses DO, SEE,
  RECORD and IF DIFFER; extend it with the actual Cedar route and exact values.
- TFK sources: `.windsurf/workflows/Edda/TFK/` and the step/fixture catalog
  artifact templates. These are playbook assets, not a materialized test library.

## TFK work required before executable acceptance coverage

The selected checkout has no configured Behave runner or materialized step and
fixture catalogs. Record this gap rather than claiming the new prose already
runs. PIN must contract the harness/catalog work and the Cedar fixture adapter
before dependent AT/E2E scenarios. Use `@wip` until a scenario's real binding and
behavior pass. Existing pytest tests continue using their normal runner.

The adapter must construct real users, released public and private playbooks,
versions, historical PIPs and ledger events. Maria's Design PIP earns 600 and
Development PIP earns 1,000; Hana and Mike are baseline v2.0. Never recalculate
historical acceptance as a fresh live award during import. Primary category,
source totals, private sentinels and all boundary people are part of the oracle.

The TFK catalog must identify every phrase's AT binding, fixture and expected
result. A browser-backed phrase belongs in the E2E layer, not the Django-client
AT layer. Provider behavior uses the existing agent proof architecture when
applicable; a canned summary fixture alone is not evidence of a live LLM call.

## Certification layers

1. AT: exact ranking, source arithmetic, privacy, event eligibility, idempotency,
   notification capture and normal PIP lifecycle through real services/DB.
2. E2E: actual navigation, query persistence, clipboard, summary expansion,
   keyboard guest explanation, contact destination and responsive geometry.
3. Visual review: actual mockup and implementation screenshots at every IA
   viewport, compared with Mimir's shared tokens and component recipes.
4. UAT: an operator completes Elena's job using DO/SEE without developer hints;
   record time and nomination, and file a defect for each mismatched step.
