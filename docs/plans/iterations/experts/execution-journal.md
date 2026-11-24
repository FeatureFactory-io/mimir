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

## S17 / N1-public-detail — NODE_PASS

- Commit 2c05351. Backend: 8 passed, 3 later-template cases deselected. Log gate: 4 passed, 7 unrelated cases deselected. Actual initial red was the unregistered detail route; all recordings retained as MIN-S17-N1-*.
- Only four assigned backend/test paths. Allowlisted public detail and generic HTTP 404 have no email/private evidence; GET is read-only. Generic rejection renders the same detail template without `person` so the N2 template can preserve the navigable shell. This is an implementation of the agreed generic 404, with no signature or footprint expansion.
- Existing request middleware logs paths app-wide; feature privacy assertions target S17's actual loggers. No global middleware change or hardening claim.
- Fresh N2 template-graduation worker dispatched. Root approved S30's recognized-category validation only for otherwise award-eligible first publication, using existing caught ValidationError. Real rejection/atomicity tests must prove it; no silent missing award or inferred category.

## Parallel node handoffs after S03

- S17/N2 a5c347a8d27318f1b208a11683c389ba42079aef: full escaped public paragraph, breakdown, public evidence links and generic navigable 404; 13 real HTTP cases. Contact stays for S14. Its future contact seam must remain request-local, without adding email/contact to the immutable public DTO.
- S17/N3 d7df811d3172e4b467ba82770b4532d05f1af6a0: exact EXPERTS-VIEW-01, 1 scenario/7 steps, zero selected skips/undefined; 13 HTTP cases. Test-only footprint added the existing shared profile-step registrations, preserving later own-profile branches. Conflict map now serializes S10 after S17; no overlapping decorators or registration-order workaround.
- S27/N1 9b6250f: real published public evidence query, modern partial/legacy aggregate/Cedar receipts; 27 behavior and 2 log cases. S27/N2 d07a7505b883598d27bfe83c40a2793a43c6eb1c: bounded layered prompt and plain-prose response validator, 45 behavior and 4 log cases. Model completion and persistence were not invoked; N3 boundary/proof worker is active.
- S30/N1 0deb13227c926bebf16d6ef9c4bf40042ed9a860: first-release atomic award once, 37 real behavior and 3 log cases; one targeted retry fixed nested Django field-error code logging. S45 pair/race helpers stay pending. S30/N2 e77602fbe6431daaef0d80fa6a31d49134f6c5bc: actual first-release earned alert and no later earned alert; 8 HTTP and 4 log cases. S30/N3 52dd232e0e7e57e1ba4375dda54b9455193669a4: exact KARMA-RELEASE-01, 1 scenario/6 steps with actual authenticated CSRF-checked POST, zero selected skips/undefined; 8 HTTP cases.

## S17 / N4-browser — NODE_FAIL; shared-style decision requested

- Six Chromium cases passed: complete signed-in paragraph plus five desktop/tablet widths. Both phone layouts stacked correctly and had no horizontal overflow, but the existing fixed Analytics preference control obscures text after consent dismissal.
- 390×844: 5×19 CSS-pixel overlap; 360×800: approximately 18×17. Actual hit-testing returned the Analytics control. Evidence retained under traces/MIN-S17-N4/phone and minimum-phone PNG/ZIP plus viewport-evidence.jsonl. The test module remains uncommitted for the failing assertions; no source workaround applied.
- Prepared one-line proposal outside the source tree: review/UX02-analytics-shared-style.patch in the recording package. It moves the shared settings button into document flow after content. Consent controls and behavior stay present.
<!-- ESCALATE -->
type: scope_expansion
severity: escalated
evidence: S17 N4 needs static/css/mimir-app.css, outside its production footprint; fixed Analytics button covers real phone prose and the list action.
jedao_recommendation: A: approve the prepared one-line shared-style fix and add the path to a bounded S17 repair node
await_human_decision: true
<!-- /ESCALATE -->
- User question was submitted through the async input tool. No answer is assumed. S17 source fixes stop while S27, S30 and independent S01 work continue. No GitHub record was created, per the user's publication waiver.

## S30 COMPLETE; S01 and S27 handoffs

- S30/N4 c6c7de212610228356f220e08cab99776c6d6cff: one real Chromium journey, actual login/modal CSRF POST, v1.0/description/single Product 5,000 award, exact earned alert and Alex/Nora order. Ninety-two trace frames retained.
- S30/N5 NODE_PASS: 34 backend cases, one exact AT/six steps, one Chromium, three named logs; separate full log module passed four including HTTP earned/not-earned branches. Independent source audit verified all ten planned log beats, atomic rollback, immutable first receipt and original API, no mocks or source/architecture escape. PG races and whole iteration still pending. S30 is complete.
- Root integrated pre-Experts CI selection after the parallel release/evidence/navigation changes: 1,636 passed, three inherited skips, 72 warnings in 119.05s. This supplements scenario gates, not unfinished contracts.
- S01/N1 58b01bea0a5693546c72fe158bd2e3f85eda52af: 31 backend, one log, 60 with inherited nav regressions. N2 d5a74c9c0ad507af118c0fc451c11f26b3162b4b: two real HTML link-follow cases. N3 431766be8dc169bf8d225a2309ea3f1c3d390e23: exact EXPERTS-LIST-01, one case/seven steps. Browser worker is active. DEBUG prototype duplication from the unmodified manual append is separately recorded; production has one canonical entry.
- S27/N3 9d75e0f303e48a22324ba7d9bdb8286aaae00ee2: nine combined, three agent proofs, five log cases; ScriptedLLM is the only stand-in, zero database writes. N4 d8d6574fbfb81e62a245e99f117d97fc75acb7ef: exact GALDR-SUMMARY-05, one case/seven steps. A test-only shared Hana background binding was reconciled in the manifest and conflict map; S23 already depends on S27.

## S27 first DoD review FAILED; bounded owner repairs

- Automated rollup passed 69 backend, one exact AT, seven log and three agent cases. Manual review nevertheless proved `Maria's Design score is 7,200.` survives both public-text redaction and output validation, violating the already agreed mutable-metric exclusion. The contract is not narrowed to hide it.
- Fresh original N1 owner is adding a real source-text regression and input redaction fix inside its existing footprint. Fresh N2 output repair follows sequentially to preserve shared-test ownership. N3 boundary has a separate one-line concision correction (31 body lines) before fresh final review. No live-provider/persistence claim.

## S47 test-only construction awaits S03 instrumentation

- Actual fixture/ORM behavior: 13 cases passed. Strict log tests found no resolver-decision records, while the four existing list-level logs were correctly captured. Test edits remain unstaged. Repeated unchanged failing selectors were diagnostic observations; no source repair has yet been attempted.
- The required trace needs real numeric account/correlation, two tied candidates/10,000 total, released-count vs alphabetical reason, selected category and unchanged total. No mocked/synthetic log or weakened assertion is accepted.
- A fresh bounded S03/N2 follow-up owns the already approved experts_service.py path, preserves the pure resolver/signatures and adds the agreed decision trace in query orchestration. This is the first targeted source fix for the missing planned instrumentation, not a S47 production footprint expansion. A fresh S47 worker will finish its test gate after that repair.

## Human decisions received — both repairs authorized

Denis answered the two pending questions explicitly:

- “Approve the shared style fix” — add static/css/mimir-app.css to a bounded S17 repair and apply the prepared one-line normal-flow placement. No further approval is needed for that exact change.
- “Fix and retry S27” — apply the prepared shared mutable-metric policy repair, add the common regression matrix and include those cases in the checkpoint. This supersedes the second-review stop for that bounded fix-and-retry.

The manifest now has fresh repair nodes R1-analytics-layout and R1-shared-metric-policy before their independent certification retries. S17's original browser assertions remain preserved; a source-only repair worker will not take ownership of the test-node commit. S27's new repair covers the two existing service modules, its existing test module and Make checkpoint configuration. Source APIs/schema remain unchanged. All 49 contracts stay in scope; there is no remote milestone/issue publication.

## Latest completed certification and repairs

- S01 N5 independently passed: 32 backend, one exact AT/seven steps, one signed-in Chromium journey, one targeted and separate log case. S01 is COMPLETE. Production has one canonical Experts link; the separately recorded DEBUG prototype append duplication remains reference maintenance.
- S47 N5 independently passed: 14 backend-gate checks, two expanded AT examples/eight steps, two Chromium cases and two strict log cases. Full backend predecessor passed all 15. S47 is COMPLETE after the bounded S03 instrumentation follow-up e8f1f9. Guest desktop scope is explicit; shared-control and full responsive review remain later gates.
- S27 repairs 9d60e961 (numeric input claims), 4d6f4c75 (output claim grammar) and 5ee0a9e (29-line completion body) passed their own gates. The second final review still proved the same written-out category score reached a real ORM→ScriptedLLM request. Its authoritative manual-orm recording and all passing automated gates are retained; the new explicit human fix-and-retry authorizes the shared-policy repair rather than narrowing the contract.
- S06 backend 50534928 (three cases), AT 5f36ac17 (one case/four steps) and browser 6e59c5fe (seven IA viewports) passed. Signed-in Feedback touches only an empty alert border at phone widths, not text/actions; no general shared-shell clearance claim. Its final DoD is pending.
- S08 backend 4e94d210 passed seven cases against the actual independent tie oracle: Alina apark and Sofia sreed both have 15,400; apark comes first, Maria remains 8,200. The helper imports exactly 30 major and four minor historical Alina awards with unknown references null, no invented public books. Root's initial dispatch shorthand about the tie subjects was corrected before code; the actual oracle governs.

## Approved repairs delivered; independent certification continues

- S17 R1-analytics-layout NODE_PASS, commit 18e2c00542cf90e2af2b0caf6c6941d3a20f00d2: only the approved shared stylesheet line. All eight profile browser cases pass, including unobstructed text at 390×844 and 360×800. Five Analytics integration cases pass. Two supplementary phone checks prove the normal-flow control opens the panel and Not now dismisses it; the first supplementary runner failed during fixture setup, and its normal-lifecycle retry is retained. Original N4 assertions were preserved unstaged for a fresh N4 completion worker. The earlier scope escalation is resolved by Denis's explicit approval.
- S02 N1-http-category-contract NODE_PASS, commit 459e2023b6cc94c1f3ded185e45842b57d6672c4: three real HTTP cases and one narrow log case. The genuine red stopped at the existing category-anchors stub. Five links, sole current Design, repeat GET order and separate safe request correlations are proved without production changes. Fresh N2 acceptance worker dispatched.
- S27 R1-shared-metric-policy NODE_PASS, commit 6858ab7d32009c019d6307dd4e9f9b29b54883b8: only the four approved source/test/Make files. Final rollup passed 104 backend, one exact AT, ten log and three agent cases, 118 unique IDs; six omitted numeric-input regressions are now included. Twenty real Cedar ORM→ScriptedLLM cases check shared input/output policy, written and comma/space-grouped values, credential/unpublished exclusion, and useful Design Score 2.0/version 2.1 controls. The prepared proposal itself still exposed grouped-number suffixes; genuine red and the minimal in-footprint correction are retained. Separate five log and three marked agent cases pass. Fresh independent N5 authorized retry dispatched. Pattern recognition is not a universal factual-grounding guarantee; no live provider/storage lifecycle claim.
- Storyboard progress paragraph and local HTML updated to Page sequence 17; all 26 scene anchors and historical evidence remain. No staging, merge, release or finished-film claim.
