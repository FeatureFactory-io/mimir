# Experts ESM handoff

## Job and scope

Elena's Cedar nomination is the acceptance anchor: person, public contribution
evidence, reason and contact handoff. The case is fictional; rank does not assert
availability or suitability. The recorded work started from the pre-Experts
baseline, not by copying the reference branch's implementation.

The six reference feature areas remain: leaderboard, public profile, contact,
own profile, contribution-summary refresh and Karma accrual. Their specification
now contains 47 scenario contracts; two existing-navigation additions bring AT scope to
49. Five separate E2E contracts and four manual UAT contracts bring the current
inventory to 58, before outline examples are expanded. This count describes
requirements, not passing feature tests. New feature scenarios remain `@wip`.

## Artifact chain

| Artifact | Actual location | State |
| --- | --- | --- |
| Brief, persona, JTD, approach decision | `docs/experts-replay/cedar-brief.txt`, `cedar-job.md` | Written and CLI-recorded |
| Journey extension | `docs/features/user_journey.md`, Act 18 | Exact routes, people, values and variants |
| Domain data contract | `test-data/experts/cedar-rfp-01.json` | Defined; model adapter belongs to implementation |
| IA and responsive contract | `docs/ux/IA_guidelines.md` §11 | Existing Mimir tokens/recipes, seven exact viewports |
| Dialogue map | `docs/ux/2_dialogue-maps/experts-flow.drawio`, `.dot`, `.svg` | Editable source and rendered flow |
| Living AT specification | `docs/features/act-18-experts/*.feature`, navigation additions | Parsed; bindings and behavior still pending |
| E2E extension | `tests/e2e/experts-journey.feature` | Browser-only jobs/geometry, separate from AT |
| UAT extension | `tests/uat/e2e-uat-flow.feature`, UAT-18 | DO/SEE/RECORD/IF DIFFER; not executed as implemented product |
| TAF assets and gaps | `docs/ux/experts-test-assets.md`, `docs/features/CATALOG.md`, `tests/fixtures/CATALOG.md` | Existing reuse mapped; scoped harness bootstrapped; Cedar adapter/bindings pending |
| Django prototypes | `/mockups/experts/`, `/mockups/experts/mrodriguez/`, `/mockups/experts/profile/`, `/mockups/experts/playbooks/6101/` | Fixture-only, shared shell/banner/inventory |
| Responsive evidence | `docs/ux/experts-responsive-evidence.json` | 77 variant/viewport renders; changed profile variants visually re-reviewed |

## Verification performed

- Gherkin parsed with the official parser, including the modified navigation,
  E2E and UAT files. Scenario IDs are unique in `scenario-index.json`.
- All eleven prototype variants rendered at all seven IA viewports. Category
  ordering, primary color, Montserrat, overflow, contact restrictions, keyboard
  explanation, summary toggle and narrow detail stacking were checked.
- Visual review found UX-01: a guest tooltip clipped left on phones despite a
  passing page-overflow check. The custom positioning was replaced by the
  existing Bootstrap tooltip and an explicit viewport-boundary assertion.
  Original and corrected evidence is retained in the session capture log.
- Implementer review restored the complete accepted-change/get-detail awards
  matrix, self-fetch exclusions, Mike's exact 47-copy fallback and category rows.
  Submission refresh now explicitly excludes all unpublished PIP titles/content;
  a public target does not turn a private proposal into public evidence.
- Actual Django-client prototype rendering returned 200 with zero DB queries.
  A separate DEBUG=False process returned 404 for the mockup URL.
- Existing mockup gating regression passed. Ruff passed for the new view module.
  These checks prove ESM prototypes, not production Experts behavior.

## Actual recording environment and evidence

Source worktree: `/Users/denispetelin/GitHub/mimir-experts-replay`, branch
`iteration/experts-replay`. The original dirty worktree is preserved. Initial
application baseline: `333c36ded6bf58bdef94049ca0f5bf98c9ce3124`.

Both isolated Docker images built, but neither the demo nor a tiny unmounted
probe started. Only those replay-owned containers were removed. The active
design server is the isolated host fallback at http://127.0.0.1:18180. Its own
SQLite DB and file-mail directory live under the production package's
`runs/session-01/`. Production/idle databases have not received Cedar records.

Capture combines real PTY cast/transcript files, Playwright videos/traces and
native Cursor screenshots. The desktop tool denied Terminal access; the Mac
later locked, pausing further native editor screenshots. Those constraints are
logged; no later view will be labeled as original keystroke footage. Narration
uses a male voice; the Daniel rehearsal is recorded.

## Next gates

The architecture/test-strategy delta and scoped TFK harness/catalog bootstrap
are recorded; their checks must pass before PIN readiness and orientation. Then
contract each scenario with actual skeleton footprints and checkpoints. Publish
the concrete issue/manifest package for PIN-05 human GO. Only then implement
production behavior through BPE inside MIN, run AT/E2E/visual/UAT, and reach the
real human merge/release gates. No production Experts feature, actual provider
summary, live acceptance run, merge or release is claimed by this handoff.
