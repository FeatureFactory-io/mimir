# Acceptance step catalog

This catalog distinguishes working test infrastructure from the Experts contract.
The living specification is not passing coverage until its binding and real
behavior run. All Experts contracts remain `@wip` during PIN planning.

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

## Pending Experts bindings

`../experts-replay/scenario-index.json` inventories 49 acceptance contracts and
their exact source locations; outline rows expand into additional cases. PIN
must assign every phrase below to real fixtures/services/HTTP assertions before
the corresponding scenario loses `@wip`.

| Phrase family | Planned real collaborators | Binding state |
| --- | --- | --- |
| CEDAR-RFP-01 baseline and independent event reset | Cedar adapter, users/playbooks/PIPs/award ledger | Pending PIN/BPE |
| Category, ranking, ties and boundary people | Experts query service, Django client | Pending PIN/BPE |
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
