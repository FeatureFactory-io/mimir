# Experts local execution journal

Denis explicitly declined GitHub milestone/issue publication, then approved:
“GO — build using the local contract”. The local iteration manifest is the
operational contract. Record scenario/node, actual gate results, commit, reason
for any deviation and next step here. Remote issue/comment requirements are
replaced by this local record under the user’s explicit instruction.

The approved scope remains all 49 acceptance contracts, five additional browser
contracts and four manual UAT contracts. Main merge/release and production
promotion retain their later human review gates. Narration uses a male voice.

## Activation

- Baseline: 333c36ded6bf58bdef94049ca0f5bf98c9ce3124.
- Structural contract handoff: 806ef2c.
- Publication declined: 6441a23.
- Start: S03 N1-schema; implement real tests and model validation first.

## S03 / N1-schema — NODE_PASS

- Commit: 8a04f1ee2f7ca73a3641e668b1bd97f3c5913333.
- Gate: `DATABASE_URL= MIMIR_ENV=test /Users/denispetelin/GitHub/mimir/.venv/bin/python -m pytest tests/integration/test_experts_schema.py -x` — 51 passed in 1.11s.
- Changed: KarmaAward/ExpertProfile validation and the existing schema test module only; no migrations or seed changes.
- Real red: `runs/session-01/cli/MIN-S03-N1-red-expanded.cast`. First implementation check caught an instance-vs-class Django manager lookup; corrected once. Final evidence: `MIN-S03-N1-green-verified.cast`.
- Scoped Ruff/Black (Python 3.12 target) passed; Django detected no migration drift.
- Test-only real fixture and parametrization expanded required edge coverage; no production methods or signatures were added.
- ORM bulk operations bypass model validation; the later importer/sole writer must validate domain inputs before bulk persistence.
- Next: N2-ledger-projection, including the already-planned formatter, HTML and logger helpers. The generic exact-acceptance runner is assigned to N4, preserving layer order. This clarifies existing scope; no product or scenario footprint expanded.

## S03 / N2-ledger-projection — NODE_PASS

- Commits: d6c78895ea95ea9644904ca47340f599ee6ce6ef (text/HTML), a1a2c53a493f2360a7aeefe22f4ee72360c67712 (projection/logs), b6ac98a0f642ad1b209d02d8bc7832b834e38d82 (data validation), a6855f494dabb3b9552eaddd93608a8d5758fdf9 (canonical history import).
- Exact behavior gate: 73 passed, 3 deliberately excluded N3 HTTP tests, in 3.70s on SQLite. Exact service log gate: 2 passed in 1.16s.
- The same behavior selection passed 73 cases in 8.17s on a new owned PostgreSQL 16 instance using CI's settings dispatcher. Django created `test_experts_replay_base`; its configured base remained empty. No ambient user database was used.
- Final recordings: `MIN-S03-N2-green-final`, `MIN-S03-N2-green-logs-final`, `MIN-S03-N2-green-postgres` under the session CLI directory. Initial intentional red recordings retained.
- Actual projection reads persisted awards across all categories; Maria 8,200 outranks Priya 7,600; Mike's 47 GUI copies remain distinct from 470 historical author-consumption events.
- Declared current activities needed workflow parents absent from the oracle. The existing playbook title supplies the minimum required current workflow label for Hana/Mike; no extra public books or historical v1 content invented. Existing explicit Maria names preserved.
- No new production methods beyond the skeleton. Private decomposition is confined to test-support importer. Scoped Ruff/Black with Python 3.12 target passed; fixture/helper ownership and method interfaces preserved.
- Next: fresh N3-direct-list-delivery worker dispatched; only list route/template and its real HTTP/log tests.

## Incremental regression accounting

All 49 contracts were scaffolded together, so unrelated future test bodies are still deliberately unimplemented. During construction, completed-node gates and an explicit inventory of 186 pre-Experts backend test files provide incremental regression evidence. This does not certify the unfinished iteration. Literal full backend and browser rollups remain required before staging/release review; pending contracts are neither skipped into a passing count nor marked complete. The file inventory is retained in the recording package as `planning/pre-experts-regression-selection.json`.

## S03 / N3-direct-list-delivery — NODE_PASS

- Commit c250f3cf6e7be4a99aac1ad18f7b7048deb87742. Real HTTP/service gate: 17 passed in 3.19s. Log gate: 5 passed in 1.83s.
- The genuine initial HTTP red was 404 for the unregistered production list route; no defect was introduced for filming. The final route reads real projections and preserves the approved Bootstrap recipe. Profile/contact destinations remain explicitly pending their later owners.
- Root separately verified browser Design → Development navigation on the loopback recording app and captured actual 1280×800 Playwright footage/screenshots. This is partial-list footage, not full journey/UAT certification.
- Root verified local demo ownership, backed it up, applied schema 0027/0028 and imported Cedar: 12 accounts, 2,129 awards, 11 summaries, exact Design order/totals. No other database seeded.

## Pre-Experts regression result after N3

- Existing CI backend selection: 182 pre-Experts files; the four existing CI file exclusions are explicit in the retained inventory. Current branch: 1,636 passed, 3 skipped, 72 warnings in 28.00s. Untouched baseline 333c36d: identical counts in 30.15s.
- Initial current-branch run stopped at 57 passes on the old activity-list raw-HTML `B1` exclusion assertion. The exact test passed separately on both baseline and current branch; the complete current-branch recheck also passed without a source change. Cause is unconfirmed; original failure and subsequent runs are retained. Do not report this as a proved baseline defect or silently discard it.
- These three inherited skips are not Experts passes. Unfinished Experts contracts remain pending; their final whole-iteration rollups are still required.

## S03 / N4-exact-acceptance — NODE_PASS

- Commit 80402d8bfd8d0b4dbdd27309d4fbc9d4a90f8da3, only the six assigned runner/step/catalog/Make files.
- Exact Make gate selected one pytest row and passed. The isolated real Behave run executed EXPERTS-LIST-03 at experts-list.feature:25: 1 selected scenario, 9 passed steps, zero selected skips/undefined. Eight unrelated scenarios were name-filtered, not claimed as passes.
- Runner validator: 19 cases passed. Revised backend rollup: 130 passed, including full owned schema/data/projection/text/HTML/HTTP modules.
- Genuine runner-stub and Cedar-Given-stub reds retained alongside final pytest/Behave recordings under MIN-S03-N4-*. Feature-level WIP remains while neighboring contracts are unfinished; explicit exact-name runner executes the selected scenario.
- Next: fresh N5 browser-order worker; no full journey, contact or detail certification claimed yet.

## S03 / N5-browser-order — NODE_PASS

- Commit 472a6ef456cc70850d267e56cb0b4565acabc71f. One real transactional-Cedar Chromium test passed in 2.82s on its first run.
- Verified five visible Design names/totals/exclusions, actual Development click, URL/current category, Mike/Jordan order/totals and Maria exclusion. No future detail/contact/summary/navigation claim.
- Genuine CLI: MIN-S03-N5-browser. Browser trace: traces/MIN-S03-N5/browser.zip, with both routes, click, DOM snapshots and eight frames. An opt-in recording hook outside the repository reused the original page context; fixture/pytest args unchanged.

## S03 / N6-definition-of-done — FIRST REVIEW FAILED

- Reviewed HEAD 472a6ef456cc70850d267e56cb0b4565acabc71f. Declared rollup passed: 130 backend, 1 exact AT (9 Behave steps), 1 Chromium, 5 log cases; separate log selection passed 5. This alone did not close S03.
- Reproducible compatibility defect in an in-memory copy of the real seed: the existing release service permits a legacy blank-category draft to release. Once its author earns one valid Design award, the Experts GET raises ValueError because released-book tie counts contain the unrelated blank category. Before that award the same GET is 200. Reproduction retained as MIN-S03-N6-legacy-category; live/tracked databases untouched.
- A fresh N2 repair worker is adding a real-DB regression and excluding unsupported legacy categories from tie-count inputs. The strict resolver and independent public-release count must remain unchanged.
- The same review found ExpertProfile.clean's body at 33 physical lines (31 nonblank). A separate fresh N1 worker is shortening layout without changing model behavior or adding methods. Both fixes stay in the original node footprints.
- Existing Analytics preference control partially overlaps the fourth Design card's action in the full-page capture. This remains explicit input to S04's full card/action visual certification; S03's partial visual check does not claim overlap-free actions.
- After the bounded repairs, a fresh N6 reviewer must rerun the terminal gate and compatibility check. S03 is still in progress; dependent scenarios have not started.

## Bounded S03 repair handoffs

- N1 repair c4593cb63c4b44f68f7f9e8c83c3e085fa900e2b: only ExpertProfile validator layout changed, 33→30 physical body lines, identical validation behavior/messages. Schema gate: 51 passed in 1.13s; scoped formatting/lint passed.
- N2 repair d641e27105a9060eca17fcfac68d84f5910c579c: only Experts query and its owned integration module. Filter unsupported current-book categories from tie inputs; independent public-release counts and strict explicit-input validation preserved. Real prior-released blank/retired-category rows now give HTTP 200, unchanged five-card ranking/totals and the correct public-count increase. Scoped behavior: 81 passed; log story: 5 passed.
- Primary original failure footage remains MIN-S03-N6-legacy-category. MIN-S03-N2-legacy-red is explicitly a comparison of the final durable regression fixture against the pre-fix query; it is not the original chronological build recording. Final green/log files are retained. The media recorder now refuses existing cast/TXT names to prevent any future overwrite; original schema-red hashes were verified unchanged by the guard check.
- A fresh read-only N6 reviewer is rechecking the complete scenario after both fixes. It may pass only the scoped S03 contract, not unfinished neighboring scenarios or full iteration delivery.

## S03 / N6-definition-of-done — NODE_PASS; S03 COMPLETE

- Fresh final reviewer accepted source d641e27105a9060eca17fcfac68d84f5910c579c, after N1 concise repair c4593cb. Rollup: 132 backend, 1 exact AT (9 Behave steps), 1 real Chromium, 5 log cases. Separate log gate: 5 passed, 14 unrelated cases deselected. Both legacy-category regressions passed with HTTP 200, unchanged ranking/totals and correct public counts.
- Evidence: MIN-S03-N6-recheck-rollup and MIN-S03-N6-recheck-log. The retry relied on durable real ORM regressions and source inspection; original seed failure remains the primary pre-fix evidence. No claim of a second cloned-seed run.
- Root post-repair pre-Experts CI selection: 1,636 passed, 3 inherited skips, 72 warnings in 27.37s. This is incremental regression evidence; unfinished Experts tests are still pending.
- Final reviewer found no remaining material S03 contract defect, source/architecture drift, new production methods or integration mocks. Partial scope and S04 Analytics-control overlap remain explicit.
- Next group: fresh nonconflicting backend nodes S17 public detail, S27 public evidence, S30 first-release awards. Original worktree and shared seed remain preserved; no merge/release/staging deployment yet.
