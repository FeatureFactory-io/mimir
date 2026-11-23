# Orient Summary — 23 November 2026

## Target and confirmed scope

Full Experts & Karma delivery from baseline 333c36d. Six Act18 feature files
plus the two Experts navigation additions. On 23 November Denis selected
“Plan all 49 acceptance contracts together.” Scope override: confirmed.
No acceptance scenario is deferred. Five browser and four manual UAT contracts
remain certification obligations mapped into the feature execution graphs.

Capture choice confirmed: genuine CLI recordings plus native Cursor screenshots.
Denis reported the Mac unlocked; native editor capture was successfully resumed.
Male narration: Daniel baseline.

## Scenarios in scope

- S01: EXPERTS-LIST-01 Open Experts from the in-app navigation (`docs/features/act-18-experts/experts-list.feature:9`)
- S02: EXPERTS-LIST-02 Preserve category selection in the URL (`docs/features/act-18-experts/experts-list.feature:17`)
- S03: EXPERTS-LIST-03 Rank Design by total points and enforce the five-person boundary (`docs/features/act-18-experts/experts-list.feature:25`)
- S04: EXPERTS-LIST-04 Show readable contribution signals and actions (`docs/features/act-18-experts/experts-list.feature:41`)
- S05: EXPERTS-LIST-05 Follow Maria to her full public evidence (`docs/features/act-18-experts/experts-list.feature:48`)
- S06: EXPERTS-LIST-06 Explain an empty category (`docs/features/act-18-experts/experts-list.feature:54`)
- S07: EXPERTS-LIST-07 Allow Bob to evaluate public rankings (`docs/features/act-18-experts/experts-list.feature:59`)
- S08: EXPERTS-LIST-08 Resolve an equal total deterministically (`docs/features/act-18-experts/experts-list.feature:66`)
- S09: EXPERTS-LIST-09 Recover an unknown category (`docs/features/act-18-experts/experts-list.feature:71`)
- S10: EXPERTS-PROFILE-01 Add contribution signals to Maria's existing profile (`docs/features/act-18-experts/experts-profile.feature:7`)
- S11: EXPERTS-PROFILE-02 Expand and collapse the long stored summary (`docs/features/act-18-experts/experts-profile.feature:15`)
- S12: EXPERTS-PROFILE-03 Display four source rows that reconcile (`docs/features/act-18-experts/experts-profile.feature:26`)
- S13: EXPERTS-PROFILE-04 Keep own-profile account controls authenticated (`docs/features/act-18-experts/experts-profile.feature:32`)
- S14: EXPERTS-REACH-01 Give authenticated Elena the correct contact destination (`docs/features/act-18-experts/experts-reach-out.feature:8`)
- S15: EXPERTS-REACH-02 Explain guest contact restriction on the list (`docs/features/act-18-experts/experts-reach-out.feature:14`)
- S16: EXPERTS-REACH-03 Apply the same guest restriction on public detail (`docs/features/act-18-experts/experts-reach-out.feature:22`)
- S17: EXPERTS-VIEW-01 Show Maria's identity and full contribution paragraph (`docs/features/act-18-experts/experts-view.feature:8`)
- S18: EXPERTS-VIEW-02 Reconcile the public score-source breakdown (`docs/features/act-18-experts/experts-view.feature:16`)
- S19: EXPERTS-VIEW-03 Follow relevant public released evidence (`docs/features/act-18-experts/experts-view.feature:22`)
- S20: EXPERTS-VIEW-04 Keep private data out of the public response (`docs/features/act-18-experts/experts-view.feature:28`)
- S21: EXPERTS-VIEW-05 Reject missing and ineligible profiles (`docs/features/act-18-experts/experts-view.feature:35`)
- S22: EXPERTS-VIEW-06 Explain a positive contributor with no public released playbook (`docs/features/act-18-experts/experts-view.feature:43`)
- S23: GALDR-SUMMARY-01 Refresh on submission without awarding acceptance points (`docs/features/act-18-experts/galdr-contribution-summary.feature:8`)
- S24: GALDR-SUMMARY-02 Present one stored summary consistently (`docs/features/act-18-experts/galdr-contribution-summary.feature:17`)
- S25: GALDR-SUMMARY-03 Refresh on normal withdrawal and resubmission (`docs/features/act-18-experts/galdr-contribution-summary.feature:23`)
- S26: GALDR-SUMMARY-04 Use a live numeric fallback without summary prose (`docs/features/act-18-experts/galdr-contribution-summary.feature:29`)
- S27: GALDR-SUMMARY-05 Exclude private data and mutable scores from generated prose (`docs/features/act-18-experts/galdr-contribution-summary.feature:35`)
- S28: GALDR-SUMMARY-06 Preserve stable prose when points change (`docs/features/act-18-experts/galdr-contribution-summary.feature:42`)
- S29: GALDR-SUMMARY-07 Preserve last good summary on provider failure (`docs/features/act-18-experts/galdr-contribution-summary.feature:49`)
- S30: KARMA-RELEASE-01 Award the first released playbook once (`docs/features/act-18-experts/karma-accrual.feature:8`)
- S31: KARMA-RELEASE-02 Do not repeat the first-release award on later versions (`docs/features/act-18-experts/karma-accrual.feature:15`)
- S32: KARMA-PIP-01 Award an accepted major ADD (`docs/features/act-18-experts/karma-accrual.feature:20`)
- S33: KARMA-PIP-02 Award an accepted minor change (`docs/features/act-18-experts/karma-accrual.feature:32`)
- S34: KARMA-PIP-03 Award only accepted changes in a partial decision (`docs/features/act-18-experts/karma-accrual.feature:59`)
- S35: KARMA-PIP-04 Do not award draft, submitted or rejected-only proposals (`docs/features/act-18-experts/karma-accrual.feature:64`)
- S36: KARMA-COPY-01 Credit a successful authenticated copy to both parties (`docs/features/act-18-experts/karma-accrual.feature:68`)
- S37: KARMA-COPY-02 Let guests copy without creating an award (`docs/features/act-18-experts/karma-accrual.feature:75`)
- S38: KARMA-COPY-03 Do not award self-copy (`docs/features/act-18-experts/karma-accrual.feature:82`)
- S39: KARMA-MCP-01 Credit eligible authenticated detail reads (`docs/features/act-18-experts/karma-accrual.feature:88`)
- S40: KARMA-MCP-03 Do not award self-fetch (`docs/features/act-18-experts/karma-accrual.feature:108`)
- S41: KARMA-MCP-02 Do not award collection listings (`docs/features/act-18-experts/karma-accrual.feature:128`)
- S42: KARMA-EXPORT-01 Credit one eligible export call regardless of file count (`docs/features/act-18-experts/karma-accrual.feature:133`)
- S43: KARMA-EXPORT-02 Do not award self-export (`docs/features/act-18-experts/karma-accrual.feature:140`)
- S44: KARMA-EXPORT-03 Do not award import (`docs/features/act-18-experts/karma-accrual.feature:145`)
- S45: KARMA-EVENT-01 Do not double-apply an event on write retry (`docs/features/act-18-experts/karma-accrual.feature:150`)
- S46: KARMA-EVENT-02 Do not award failed or unauthorized consumption (`docs/features/act-18-experts/karma-accrual.feature:157`)
- S47: KARMA-CATEGORY-01 Resolve primary-category ties (`docs/features/act-18-experts/karma-accrual.feature:161`)
- S48: FOB-NAV-EXPERTS-01 Discover Experts in the existing app sidebar (`docs/features/act-0-auth/navigation.feature:103`)
- S49: FOB-NAV-EXPERTS-02 Guest Experts navigation stays public (`docs/features/act-0-auth/navigation.feature:111`)

## Learning evidence and risk

See pin-readiness-20261123-experts.md for the three inspected historical reports.
Metrics lack standard frontmatter; velocity/footprint trends are unknown.
No scenario is declared implemented by empty/skipped checkpoints. Risks are
scope size, shared ledger/query/profile files, permission-sensitive consumption,
public-summary privacy, and the recorded Docker fallback. Merge/release need
review after real implementation and certification.

## PIN-03 execution plan

1. Dispatch exactly one pure-analysis worker per acceptance contract, in waves
   of up to three (available concurrency). Each reads shared SAO, journey, data,
   relevant source bodies/tests and live guidance snapshot. No worker writes
   files or commits: planning write footprints are empty, all pairs independent.
2. Each returns BPE-01 A–H, feature graph, exact test/log/agent gates, proposed
   implementation footprint and complete typed/docstring skeleton text.
3. Collect all 49 reports, batch infrastructure/scope proposals requiring a
   decision, and reconcile shared-file creation/interface ownership before writes.
4. Apply only unimplemented structural skeletons sequentially, checking behavior
   and log/agent commands for expected NotImplementedError/zero collection.
   Syntax/import errors must be corrected. Commit each scenario separately and
   derive its actual git footprint and skeleton SHA.
5. Derive the file conflict map and execution groups from real commits. Publish
   the full manifest and self-contained issue plans through PIN-04. Obtain the
   later PIN-05 human GO before any Experts behavior/test bodies are filled.

Read/write boundaries: workers read the replay only and return reports. Parent
owns plan documents, sequential skeleton application and GitHub publication.
Preserve original dirty worktree. No live provider call, deployment, seed reset,
main merge or release during this contracting phase.
