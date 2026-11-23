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
