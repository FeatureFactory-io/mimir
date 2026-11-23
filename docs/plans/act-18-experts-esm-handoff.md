# Experts ESM handoff

## Job and scope

Elena's Cedar nomination is the acceptance anchor: person, public contribution
evidence, reason and contact handoff. The case is fictional; rank does not assert
availability or suitability. The recorded work started from the pre-Experts
baseline, not by copying the reference branch's implementation.

The six reference feature areas remain: leaderboard, public profile, contact,
own profile, contribution-summary refresh and Karma accrual. Their specification
contains 49 planned acceptance contracts, including the two navigation additions.
The PIN review places 43 in Django-client AT and six actual-interaction contracts
in browser certification. Five additional journey/viewport contracts and four
manual UAT contracts preserve 58 unique IDs. Outline expansion yields 83 server
AT cases and 23 browser cases, plus four manual UAT contracts. These are
requirements counts, not passing feature tests. All remain `@wip`.

## Artifact chain

| Artifact | Actual location | State |
| --- | --- | --- |
| Brief, persona, JTD, approach decision | `docs/experts-replay/cedar-brief.txt`, `cedar-job.md` | Written and CLI-recorded |
| Journey extension | `docs/features/user_journey.md`, Act 18 | Exact routes, people, values and variants |
| Domain data contract | `test-data/experts/cedar-rfp-01.json` | Defined; model adapter belongs to implementation |
| IA and responsive contract | `docs/ux/IA_guidelines.md` §11 | Existing Mimir tokens/recipes, seven exact viewports |
| Dialogue map | `docs/ux/2_dialogue-maps/experts-flow.drawio`, `.dot`, `.svg` | Editable source and rendered flow |
| Living AT specification | `docs/features/act-18-experts/*.feature`, `docs/features/act-0-auth/experts-navigation.feature` | 43 parsed contracts; bindings and behavior still pending |
| Browser acceptance and E2E extension | `tests/e2e/experts-interactions.feature`, `experts-journey.feature` | Six full interaction contracts plus five jobs/viewport contracts; separate from AT |
| UAT extension | `tests/uat/e2e-uat-flow.feature`, UAT-18 | DO/SEE/RECORD/IF DIFFER; not executed as implemented product |
| TAF assets and gaps | `docs/ux/experts-test-assets.md`, `docs/features/CATALOG.md`, `tests/fixtures/CATALOG.md` | Existing reuse mapped; scoped harness bootstrapped; Cedar adapter/bindings pending |
| Django prototypes | `/mockups/experts/`, `/mockups/experts/mrodriguez/`, `/mockups/experts/profile/`, `/mockups/experts/playbooks/6101/` | Fixture-only, shared shell/banner/inventory |
| Responsive evidence | `docs/ux/experts-responsive-evidence.json` | 77 variant/viewport renders; changed profile variants visually re-reviewed |

## Verification performed

- The official parser accepts all scoped Experts server and browser specification
  files. Scenario IDs remain unique in `scenario-index.json`. The two Experts
  navigation additions were relocated from malformed legacy prose with an
  unrelated authenticated Background into their own Cedar-backed feature.
  The six browser-backed contracts moved without changing any statement or ID;
  clipboard, hover and visual layout are not simulated in Django-client AT.
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
native Cursor screenshots, as Denis selected. Capture resumed after he unlocked
the Mac; a later lock paused new native frames. CLI/browser recording continues.
The CLI export rehearsal preserves actual output and timing, labels replay and
source hash, and passed H.264/yuv420p/1080p inspection. No later view is labeled
as original keystroke footage. Narration uses a male voice; Daniel was rehearsed.

## Next gates

The architecture/test-strategy delta and scoped TFK prerequisites passed their
recorded checks. Denis confirmed all 49 contracts together; every dedicated
read-only planning report has returned. Reconcile the complete plans, then
apply only structural unimplemented skeletons with actual footprints/checkpoints.
Publish
the concrete issue/manifest package for PIN-05 human GO. Only then implement
production behavior through BPE inside MIN, run AT/E2E/visual/UAT, and reach the
real human merge/release gates. No production Experts feature, actual provider
summary, live acceptance run, merge or release is claimed by this handoff.
