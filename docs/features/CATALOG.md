# Acceptance step catalog

This catalog tracks reusable acceptance bindings and executed Experts contracts.
`EXPERTS-LIST-03` passed through the exact runner. Its feature-level `@wip`
tag still protects unfinished scenarios from the broad acceptance command.

## Implemented reusable primitives

| Phrase | Binding | State and verification |
| --- | --- | --- |
| Given an anonymous AT visitor | `steps/http_steps.py:anonymous_visitor` | Logs out the real Django client |
| When the AT visitor requests "{path}" | `steps/http_steps.py:request_path` | Local absolute path only; real GET, response retained |
| Then the AT response status is {status:d} | `steps/http_steps.py:response_status` | Compares actual response status |

Lifecycle: `environment.py:django_ready` exposes `context.test.client` supplied by
`behave-django --simple`; Django creates and destroys the isolated test database.
`mimir.settings.acceptance` forces in-memory SQLite and local-memory mail.
No browser, live model, domain mock or running demo DB is used.

Prove the infrastructure with `make test-at-harness`. Its single golden feature
is `act-0-auth/test-harness.feature`. It is a harness check, not Experts AT.
`make test-at-experts` targets only the Experts directory plus its navigation
extensions. A run selecting zero implemented contracts must be reported as zero
coverage. Some unrelated historical feature prose is not parser-ready; a broad
`manage.py behave docs/features` run is not the acceptance command for this work.

## Executed Experts bindings

`make test-experts-s03-at` runs exactly `EXPERTS-LIST-03` from
`act-18-experts/experts-list.feature` through `manage.py behave --simple` and
`mimir.settings.acceptance`. The runner opts this exact name into execution
despite its inherited `@wip` tag. It requires one passed case and nine passed
steps, including the background. Selection checks reject a matching skipped
case and tolerate unrelated cases reported as skipped by the name filter.

| Phrase family | Binding in `steps/experts_steps.py` | Real collaborator |
| --- | --- | --- |
| CEDAR-RFP-01 baseline | `cedar_baseline_dataset` | Isolated ORM fixture importer |
| Elena, he or Bob opens a path | `elena_opens_experts` | Local Django-client GET with the current session |
| Ranked usernames and Design exclusions | `ranked_usernames_match_table`, `contributor_is_absent` | Rendered ordered cards and live view scores |
| Switch to Development, rank Mike before Jordan, exclude Maria | `elena_selects_development`, `development_order_matches_contract`, `maria_secondary_category_is_excluded` | Rendered category link, cards and live primary-category projection |

## Pending Experts bindings

`../experts-replay/scenario-index.json` inventories 49 acceptance contracts and
their exact source locations; outline rows expand into additional cases. PIN
must assign every phrase below to real fixtures/services/HTTP assertions before
the corresponding scenario loses `@wip`.

| Phrase family | Planned real collaborators | Binding state |
| --- | --- | --- |
| Independent event resets | Cedar adapter, users/playbooks/PIPs/award ledger | Pending BPE |
| Other category interactions, ties and boundary cases | Experts query service, Django client | Pending BPE |
| Public detail, private exclusions, guest access | Existing permission services, real views | Pending PIN/BPE |
| Own-profile summary and contribution rows | Existing profile view, summary/ledger projection | Pending PIN/BPE |
| Contact destination/restriction | Real rendered HTML; browser focus in E2E | Pending PIN/BPE |
| First release and accepted/partial PIP changes | Existing release/decision lifecycle, award service | Pending PIN/BPE |
| Successful copy, authorized MCP reads/exports | Real service/REST/facade path and event record | Pending PIN/BPE |
| Summary request, refresh/failure/privacy | Real public-evidence service and ScriptedLLM seam | Pending PIN/BPE |
| Notification capture and retry identity | Real EmailService/locmem and persisted event IDs | Pending PIN/BPE |

Geometry, clipboard, tooltips, tab persistence and expansion interactions belong
to `tests/e2e/experts-journey.feature` and Playwright implementations, not this
Django-client step library. Manual DO/SEE/RECORD belongs to UAT.

## Experts replay planning registration

The table inventories the planned contracts. Only the S03 server acceptance
case has passed through the exact runner.

| PIN | Contract | Authoritative source | Primary layer | Cases | Gate |
|---|---|---|---|---:|---|
| S01 | EXPERTS-LIST-01 | `docs/features/act-18-experts/experts-list.feature:9` | at | 1 | `make test-experts-s01` |
| S02 | EXPERTS-LIST-02 | `docs/features/act-18-experts/experts-list.feature:17` | at | 1 | `make test-experts-s02` |
| S03 | EXPERTS-LIST-03 | `docs/features/act-18-experts/experts-list.feature:25` | at | 1 | `make test-experts-s03` |
| S04 | EXPERTS-LIST-04 | `docs/features/act-18-experts/experts-list.feature:41` | at | 1 | `make test-experts-s04` |
| S05 | EXPERTS-LIST-05 | `docs/features/act-18-experts/experts-list.feature:48` | at | 1 | `make test-experts-s05` |
| S06 | EXPERTS-LIST-06 | `docs/features/act-18-experts/experts-list.feature:54` | at | 1 | `make test-experts-s06` |
| S07 | EXPERTS-LIST-07 | `docs/features/act-18-experts/experts-list.feature:59` | at | 1 | `make test-experts-s07` |
| S08 | EXPERTS-LIST-08 | `docs/features/act-18-experts/experts-list.feature:66` | at | 1 | `make test-experts-s08` |
| S09 | EXPERTS-LIST-09 | `docs/features/act-18-experts/experts-list.feature:71` | at | 1 | `make test-experts-s09` |
| S10 | EXPERTS-PROFILE-01 | `docs/features/act-18-experts/experts-profile.feature:7` | at | 1 | `make test-experts-s10` |
| S11 | EXPERTS-PROFILE-02 | `tests/e2e/experts-interactions.feature:9` | e2e | 1 | `make test-experts-s11` |
| S12 | EXPERTS-PROFILE-03 | `docs/features/act-18-experts/experts-profile.feature:15` | at | 1 | `make test-experts-s12` |
| S13 | EXPERTS-PROFILE-04 | `docs/features/act-18-experts/experts-profile.feature:21` | at | 1 | `make test-experts-s13` |
| S14 | EXPERTS-REACH-01 | `docs/features/act-18-experts/experts-reach-out.feature:8` | at | 1 | `make test-experts-s14` |
| S15 | EXPERTS-REACH-02 | `tests/e2e/experts-interactions.feature:21` | e2e | 1 | `make test-experts-s15` |
| S16 | EXPERTS-REACH-03 | `docs/features/act-18-experts/experts-reach-out.feature:14` | at | 1 | `make test-experts-s16` |
| S17 | EXPERTS-VIEW-01 | `docs/features/act-18-experts/experts-view.feature:8` | at | 1 | `make test-experts-s17` |
| S18 | EXPERTS-VIEW-02 | `docs/features/act-18-experts/experts-view.feature:16` | at | 1 | `make test-experts-s18` |
| S19 | EXPERTS-VIEW-03 | `docs/features/act-18-experts/experts-view.feature:22` | at | 1 | `make test-experts-s19` |
| S20 | EXPERTS-VIEW-04 | `docs/features/act-18-experts/experts-view.feature:28` | at | 1 | `make test-experts-s20` |
| S21 | EXPERTS-VIEW-05 | `docs/features/act-18-experts/experts-view.feature:35` | at | 2 | `make test-experts-s21` |
| S22 | EXPERTS-VIEW-06 | `docs/features/act-18-experts/experts-view.feature:43` | at | 1 | `make test-experts-s22` |
| S23 | GALDR-SUMMARY-01 | `docs/features/act-18-experts/galdr-contribution-summary.feature:8` | at | 1 | `make test-experts-s23` |
| S24 | GALDR-SUMMARY-02 | `tests/e2e/experts-interactions.feature:30` | e2e | 1 | `make test-experts-s24` |
| S25 | GALDR-SUMMARY-03 | `docs/features/act-18-experts/galdr-contribution-summary.feature:17` | at | 1 | `make test-experts-s25` |
| S26 | GALDR-SUMMARY-04 | `docs/features/act-18-experts/galdr-contribution-summary.feature:23` | at | 1 | `make test-experts-s26` |
| S27 | GALDR-SUMMARY-05 | `docs/features/act-18-experts/galdr-contribution-summary.feature:29` | at | 1 | `make test-experts-s27` |
| S28 | GALDR-SUMMARY-06 | `docs/features/act-18-experts/galdr-contribution-summary.feature:36` | at | 1 | `make test-experts-s28` |
| S29 | GALDR-SUMMARY-07 | `docs/features/act-18-experts/galdr-contribution-summary.feature:43` | at | 1 | `make test-experts-s29` |
| S30 | KARMA-RELEASE-01 | `docs/features/act-18-experts/karma-accrual.feature:8` | at | 1 | `make test-experts-s30` |
| S31 | KARMA-RELEASE-02 | `docs/features/act-18-experts/karma-accrual.feature:15` | at | 1 | `make test-experts-s31` |
| S32 | KARMA-PIP-01 | `docs/features/act-18-experts/karma-accrual.feature:20` | at | 3 | `make test-experts-s32` |
| S33 | KARMA-PIP-02 | `docs/features/act-18-experts/karma-accrual.feature:32` | at | 20 | `make test-experts-s33` |
| S34 | KARMA-PIP-03 | `docs/features/act-18-experts/karma-accrual.feature:59` | at | 1 | `make test-experts-s34` |
| S35 | KARMA-PIP-04 | `docs/features/act-18-experts/karma-accrual.feature:64` | at | 1 | `make test-experts-s35` |
| S36 | KARMA-COPY-01 | `tests/e2e/experts-interactions.feature:37` | e2e | 1 | `make test-experts-s36` |
| S37 | KARMA-COPY-02 | `tests/e2e/experts-interactions.feature:45` | e2e | 1 | `make test-experts-s37` |
| S38 | KARMA-COPY-03 | `tests/e2e/experts-interactions.feature:53` | e2e | 1 | `make test-experts-s38` |
| S39 | KARMA-MCP-01 | `docs/features/act-18-experts/karma-accrual.feature:68` | at | 9 | `make test-experts-s39` |
| S40 | KARMA-MCP-03 | `docs/features/act-18-experts/karma-accrual.feature:88` | at | 10 | `make test-experts-s40` |
| S41 | KARMA-MCP-02 | `docs/features/act-18-experts/karma-accrual.feature:108` | at | 1 | `make test-experts-s41` |
| S42 | KARMA-EXPORT-01 | `docs/features/act-18-experts/karma-accrual.feature:113` | at | 1 | `make test-experts-s42` |
| S43 | KARMA-EXPORT-02 | `docs/features/act-18-experts/karma-accrual.feature:120` | at | 1 | `make test-experts-s43` |
| S44 | KARMA-EXPORT-03 | `docs/features/act-18-experts/karma-accrual.feature:125` | at | 1 | `make test-experts-s44` |
| S45 | KARMA-EVENT-01 | `docs/features/act-18-experts/karma-accrual.feature:130` | at | 1 | `make test-experts-s45` |
| S46 | KARMA-EVENT-02 | `docs/features/act-18-experts/karma-accrual.feature:137` | at | 1 | `make test-experts-s46` |
| S47 | KARMA-CATEGORY-01 | `docs/features/act-18-experts/karma-accrual.feature:141` | at | 2 | `make test-experts-s47` |
| S48 | FOB-NAV-EXPERTS-01 | `docs/features/act-0-auth/experts-navigation.feature:8` | at | 1 | `make test-experts-s48` |
| S49 | FOB-NAV-EXPERTS-02 | `docs/features/act-0-auth/experts-navigation.feature:16` | at | 1 | `make test-experts-s49` |

Shared Cedar data: `test-data/experts/cedar-rfp-01.json`; adapter `tests/support/experts_data.py`, runner-owned or verified demo DB only. Five journey/viewport and four manual UAT contracts remain separately mapped in `docs/plans/iterations/pin-convergence-20261123-experts.md`.
