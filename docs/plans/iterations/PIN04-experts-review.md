# Experts replay: local execution contract

All 49 acceptance contracts are planned together, as requested. This package
contains the scenario plans, unimplemented application/test scaffolds, actual
commit footprints and the execution manifest. Implementation has not begun.

Denis declined GitHub publication: “No, skip this part.” No milestone or issues
were created. The 49 drafts and the complete manifest remain local. Any future
execution uses this local contract; implementation GO has not been recorded.

## Product and film result

Elena evaluates contributors for Noor’s Cedarbank RFP: select Design, compare
Sofia and Maria, inspect Maria’s real public playbook/workflow evidence and
identify her contact destination. Bob can inspect that evidence and receives
a clear sign-in explanation for contact. Maria can reconcile her record, see
a summary refreshed on submission without points, then earn the accepted-change
award after the real administrator decision. Actual copy/MCP/export events have
atomic, retry-safe awards; guest/self/list/import/failure cases earn zero.

The film retains the precise storyboard and real work capture. CLI recordings
and native Cursor screenshots are selected; narration uses a male voice. The
20–30 minute runtime is an edited narrative, not a claim about elapsed build time.

## Evidence so far

- 49 dedicated planning reports converged into 49 sequential scaffold commits.
- 907 new callable bodies remain raising; 371 pre-existing callable ASTs are unchanged.
- 83 server acceptance examples / 410 steps have complete unambiguous registrations; dry-run only.
- 620 backend and 124 browser tests collect; all 116 declared pytest selections collect positively and all 133 Make targets resolve. These are structural checks, not feature passes.
- 29 existing profile/release/model-seam regressions passed.
- Real 0027/0028 schema is in the replay seed, with empty Experts tables and only expected Django migration/content-type/permission metadata additions. No Cedar data was seeded.
- The original Mimir working tree was preserved. No staging deployment or release has occurred.

## Contract and sequencing

[Consolidated domain and verification contract](pin-convergence-20261123-experts.md) ·
[Full execution manifest](ITER-20261123-experts-replay.yaml) ·
[Scenario source index](../../experts-replay/scenario-index.json).

The actual conflict map contains 26 shared paths. Seven dependency-ordered groups
serialize overlapping files. Each build node receives a fresh agent, an exact
footprint, the relevant BPE guidance and real gates. The 43 server acceptance
contracts and six browser interaction contracts remain one 49-contract scope;
five additional browser and four manual UAT obligations preserve 58 unique IDs.

| Group | Scenarios |
|---|---|
| A | S03 |
| B | S01, S06, S08, S10, S17, S27, S30, S47 |
| C | S02, S07, S09, S11, S12, S13, S14, S19, S21, S22, S23, S36, S48 |
| D | S04, S18, S20, S25, S32, S37, S39, S49 |
| E | S28, S45, S05, S15, S24, S26, S31, S33, S38, S40, S41, S42 |
| F | S29, S35, S16, S43, S44, S46 |
| G | S34 |

## Exact issue drafts

| Scenario | Contract | Group | Dependencies | Draft |
|---|---|---|---|---|
| S03 | EXPERTS-LIST-03 | A | none | [Read](experts/issues/S03.md) |
| S01 | EXPERTS-LIST-01 | B | S03 | [Read](experts/issues/S01.md) |
| S06 | EXPERTS-LIST-06 | B | S03 | [Read](experts/issues/S06.md) |
| S08 | EXPERTS-LIST-08 | B | S03 | [Read](experts/issues/S08.md) |
| S10 | EXPERTS-PROFILE-01 | B | S03 | [Read](experts/issues/S10.md) |
| S17 | EXPERTS-VIEW-01 | B | S03 | [Read](experts/issues/S17.md) |
| S27 | GALDR-SUMMARY-05 | B | S03 | [Read](experts/issues/S27.md) |
| S30 | KARMA-RELEASE-01 | B | S03 | [Read](experts/issues/S30.md) |
| S47 | KARMA-CATEGORY-01 | B | S03 | [Read](experts/issues/S47.md) |
| S02 | EXPERTS-LIST-02 | C | S03, S01, S47 | [Read](experts/issues/S02.md) |
| S07 | EXPERTS-LIST-07 | C | S03, S01 | [Read](experts/issues/S07.md) |
| S09 | EXPERTS-LIST-09 | C | S03, S01 | [Read](experts/issues/S09.md) |
| S11 | EXPERTS-PROFILE-02 | C | S10 | [Read](experts/issues/S11.md) |
| S12 | EXPERTS-PROFILE-03 | C | S03, S10, S06 | [Read](experts/issues/S12.md) |
| S13 | EXPERTS-PROFILE-04 | C | S10 | [Read](experts/issues/S13.md) |
| S14 | EXPERTS-REACH-01 | C | S03, S17 | [Read](experts/issues/S14.md) |
| S19 | EXPERTS-VIEW-03 | C | S17, S27 | [Read](experts/issues/S19.md) |
| S21 | EXPERTS-VIEW-05 | C | S17 | [Read](experts/issues/S21.md) |
| S22 | EXPERTS-VIEW-06 | C | S17 | [Read](experts/issues/S22.md) |
| S23 | GALDR-SUMMARY-01 | C | S03, S27 | [Read](experts/issues/S23.md) |
| S36 | KARMA-COPY-01 | C | S03, S30, S17 | [Read](experts/issues/S36.md) |
| S48 | FOB-NAV-EXPERTS-01 | C | S01, S03 | [Read](experts/issues/S48.md) |
| S04 | EXPERTS-LIST-04 | D | S03, S17, S14, S10 | [Read](experts/issues/S04.md) |
| S18 | EXPERTS-VIEW-02 | D | S12, S17, S03 | [Read](experts/issues/S18.md) |
| S20 | EXPERTS-VIEW-04 | D | S03, S17, S14 | [Read](experts/issues/S20.md) |
| S25 | GALDR-SUMMARY-03 | D | S23, S27 | [Read](experts/issues/S25.md) |
| S28 | GALDR-SUMMARY-06 | E | S23, S10, S11, S12, S36, S27, S25 | [Read](experts/issues/S28.md) |
| S32 | KARMA-PIP-01 | D | S30, S23, S10, S11, S12, S03, S27, S36 | [Read](experts/issues/S32.md) |
| S37 | KARMA-COPY-02 | D | S03, S07, S36 | [Read](experts/issues/S37.md) |
| S39 | KARMA-MCP-01 | D | S03, S30, S36, S17 | [Read](experts/issues/S39.md) |
| S45 | KARMA-EVENT-01 | E | S30, S36, S32 | [Read](experts/issues/S45.md) |
| S49 | FOB-NAV-EXPERTS-02 | D | S01, S07 | [Read](experts/issues/S49.md) |
| S05 | EXPERTS-LIST-05 | E | S04, S17, S19 | [Read](experts/issues/S05.md) |
| S15 | EXPERTS-REACH-02 | E | S04, S07, S14 | [Read](experts/issues/S15.md) |
| S24 | GALDR-SUMMARY-02 | E | S23, S04, S10, S11, S17 | [Read](experts/issues/S24.md) |
| S26 | GALDR-SUMMARY-04 | E | S03, S04, S10, S17, S27, S25 | [Read](experts/issues/S26.md) |
| S29 | GALDR-SUMMARY-07 | F | S23, S04, S10, S17, S27, S25, S28, S26 | [Read](experts/issues/S29.md) |
| S31 | KARMA-RELEASE-02 | E | S30, S32 | [Read](experts/issues/S31.md) |
| S33 | KARMA-PIP-02 | E | S32 | [Read](experts/issues/S33.md) |
| S35 | KARMA-PIP-04 | F | S32, S03, S27, S33 | [Read](experts/issues/S35.md) |
| S38 | KARMA-COPY-03 | E | S03, S30, S36, S37 | [Read](experts/issues/S38.md) |
| S40 | KARMA-MCP-03 | E | S39 | [Read](experts/issues/S40.md) |
| S41 | KARMA-MCP-02 | E | S03, S39, S23 | [Read](experts/issues/S41.md) |
| S42 | KARMA-EXPORT-01 | E | S03, S30, S36, S39 | [Read](experts/issues/S42.md) |
| S16 | EXPERTS-REACH-03 | F | S03, S07, S14, S15, S17, S20, S06, S21 | [Read](experts/issues/S16.md) |
| S34 | KARMA-PIP-03 | G | S32, S33, S03, S27, S35 | [Read](experts/issues/S34.md) |
| S43 | KARMA-EXPORT-02 | F | S42 | [Read](experts/issues/S43.md) |
| S44 | KARMA-EXPORT-03 | F | S03, S23, S39, S41, S42 | [Read](experts/issues/S44.md) |
| S46 | KARMA-EVENT-02 | F | S36, S39, S42, S45 | [Read](experts/issues/S46.md) |

## Recorded publication decision

The repository’s [PIN-04 Publish](../../../.windsurf/workflows/Edda/PIN/PIN-04-Publish.md) says: “Ask user before creating.” Its Step 1 asks whether to create the milestone and issues from the manifest. Denis declined this publication step. No external record has been created.
