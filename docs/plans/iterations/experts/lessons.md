# Experts replay: lessons supported by the work

This record supports the staging-only replay. It does not certify a production
release or a completed staged UAT run. The accepted feature specification and
actual evidence remain authoritative.

## Choose data that distinguishes plausible implementations

The Design leaderboard filters by primary playbook category and then ranks by
all-category Karma. If every contributor earns points only in Design, sorting
by the Design subtotal produces the same answer. Such a fixture cannot expose
the alternative interpretation, even when its checks pass.

The accepted Cedar example deliberately separates those values:

| Contributor | All-category total | Design subtotal |
| --- | ---: | ---: |
| Maria Rodriguez | 8,200 | 7,200 |
| Priya Nair | 7,600 | 7,600 |

Maria must precede Priya. Sorting by Design subtotal would reverse them. This
single pair gives the implementation and its verifier a concrete disagreement
to resolve. Source: `docs/features/act-18-experts/experts-list.feature`, scenario
EXPERTS-LIST-03; data: `test-data/experts/cedar-rfp-01.json`.

The same principle supplies separate boundary people: Theo is an eligible sixth
Design contributor, Mike has points but a Development primary category, and
Nora has zero Karma. Five eligible people alone cannot prove a top-five cutoff;
a high-scoring person alone cannot prove the category filter.

## A job requires evidence beyond a ranking

Elena's Cedar job is to nominate a plausible contributor for a discussion, inspect
the full summary and a relevant released public playbook, and find the correct
contact handoff. Sofia's higher score does not itself establish fit for accessible
form review. Maria's relevant public work supports the nomination. Availability,
hiring suitability and email delivery remain unconfirmed. The browser journey
must reach the actual playbook identity and contact target, rather than merely
return successful HTTP statuses.

## Convergence includes supported neighbors and test isolation

Independent scenario completion did not establish whole-project correctness.
The first complete run exposed test fixtures leaking a private async connection
and an old migration state into later cases. The real older-server/new-client
matrix also exposed a product compatibility defect: a successful read or export
could be followed by a failed unsupported receipt request. The resulting API
response capability header preserves older native results while retaining strict
checks when receipt support is advertised. The execution journal links the
original failures, repairs and independent proofs.

## Deployment identity includes the database

The SAO declares that the normal idle and live environments share RDS database
`mimir`. An idle hostname therefore does not establish test-data isolation.
Cedar requires a positively verified owned companion database before migration
or fixture writes. Source SHA, immutable image digest, actual source-file checks,
database ownership and browser observations belong together in the staging
record. Local proof is not a deployed UAT verdict. This assignment ends at
staging with that isolated test database.
