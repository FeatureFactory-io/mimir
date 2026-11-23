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
