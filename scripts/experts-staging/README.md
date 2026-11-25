# Experts on idle with the Cedar test database

This runner stops at isolated staging with its own test database. The user's
boundary is explicit: do not release to production or go past staging. This
runner cannot merge main, publish a release, deploy the normal EB application,
swap CNAMEs or promote production.

Preparation is complete only after the local contract checks and independent
review. An actual successful candidate image build and an explicit dispatch of
the reviewed isolated mode are still needed before any staging result exists.

## Dispatch

Use the existing registered `build-and-deploy.yml` workflow on the reviewed
iteration branch with these inputs:

```text
experts_staging_only=true
experts_candidate_run_id=<actual successful build-only run ID>
experts_candidate_sha=<that run's exact forty-character source SHA>
deploy_to_idle=false
preflight_only=false
wake_idle=false
```

The default `experts_staging_only=false` preserves the normal workflow. When
isolated mode is true, normal test migrations, image build/deploy, idle power and
preflight jobs skip. Its first step rejects contradictory input flags before AWS
configuration. The candidate must be an actual successful iteration build-only
run with tests/build succeeded and the normal idle deployment skipped.

## Source and database identity

The candidate build's Actions artifact binds its Git SHA/run to an immutable ECR
web-image digest. `source.json` independently hashes the actual Docker-included
application, template, asset, guard and Cedar fixture files from that Git object.
The exact image files must match before Django opens. The candidate Dockerfile
has no embedded source-SHA label; the receipt does not claim one.

The control harness can be newer than the candidate. Its separate runner Git SHA
is recorded. Reviewed runtime/settings files mount outside `/app`; they do not
replace application code. The browser derivative builds from that exact web
image, adds only Chromium/dependencies, and receives its own immutable digest.
Actual image sizes plus reserve are checked against fresh host disk capacity;
pulls also retain a live oneGiB free-space floor. Nothing prunes ambient images.

The existing physical idle environment is rediscovered from current live-CNAME
ownership, instance tags, architecture and SSM status. No host is created or woken.
The normal idle/production RDS database is never read for configuration or seeded.

An internal Docker network contains only the owned web/PG/browser companions.
PostgreSQL16 has a fresh data directory and random admin password. The app role
has LOGIN and none of SUPERUSER, CREATEDB, CREATEROLE, BYPASSRLS or REPLICATION.
Its database/role name, owner, catalog comment, actual connection and private
mode0700/mode0600 marker must match `CedarDatabaseScope('owned_staging', ...)`
before migrations or fixture import. Import runs once; no reset path is included.
The recording starts with12users,2,129awards and11profiles. The complete domain
snapshot is checked after anonymous browsing/copying.

## Runtime differences

The settings overlay imports the actual production settings and retains the
real templates, Bootstrap/Montserrat styling, middleware and domain services.
It explicitly changes the database to the owned PG container without DB TLS,
allows only local companion hosts/origin, writes mail to the owned file directory,
and collects actual static files into an owned mount. It has a fresh app secret,
no external provider/GitHub/SES/AWS credentials and no normal admin bootstrap.

Gunicorn serves private HTTPS with a short-lived self-signed certificate.
Chromium trusts only that certificate's public-key pin; it does not enable global
certificate-error ignoring or an unsafe-origin secure-context bypass. Native
`window.isSecureContext` and actual clipboard write/read/completion are checked.
The inherited image healthcheck for port8000 is disabled; readiness instead checks
the actual certificate, TLS endpoint, database health and identified source.

The web container gets384MiB/0.75CPU, PostgreSQL192MiB/0.25CPU and the browser
512MiB/1CPU. All have memory-swap bounds, process limits, dropped capabilities,
read-only roots and owned writable mounts. The browser has a separate labeled
egress bridge for real external shell assets. Its request policy continues real
requests only to the owned origin and the six domains observed in original
browser traces: Google Fonts, jsDelivr, Font Awesome kit/ka-p and unpkg. It never
fabricates a response. Both Montserrat and Font Awesome6Pro must actually load;
a missing-font acquisition is retained before at most one real recapture.

## What core readiness proves

`browser.py` records fourteen guest list/profile views at all seven IA sizes,
plus a real anonymous native-clipboard copy of public activity6203. It checks
actual ordered names, private-sentinel absence, geometry, fonts, secure context,
exact server-built public-prompt digest/length and absence of guest receipt
attempts. The server then rechecks actual DB ownership, all baseline domain rows
and absence of decision-mail files. The verdict is `SMOKE_ONLY_UAT_PENDING`.
Its elapsed time measures the automated on-idle operator run, not human task time.

## Full Saga follow-up

The core readiness driver does not substitute for these accepted contracts:

| Contract | Existing source and additional staging work |
| --- | --- |
| CEDAR-JOURNEY-01 / UAT-18-01 | `tests/e2e/test_experts_cedar_nomination.py`: Elena's actual sidebar, Sofia comparison, Maria evidence, public playbook/workflow, correct handoff and measured external nomination. |
| CEDAR-JOURNEY-02 / UAT-18-02 | `tests/e2e/test_experts_guest_detail.py` and guest navigation/contact tests: keyboard explanation, Other empty state, missing/Nora404 and full public evidence. |
| CEDAR-JOURNEY-03 | `tests/e2e/test_experts_summary_stability.py`: own-profile/source reading, authenticated real copy to8,205 and unchanged stored prose. |
| EXPERTS-LIST-10 | `tests/e2e/test_expert_cards.py`: approved full normal/long/missing/guest card matrix at seven viewports, not only the core guest views. |
| EXPERTS-VIEW-07 | Existing guest/detail/profile view tests: body/rail order, stacking, full keyboard/contact/evidence behavior and visual comparison. |
| UAT-18-03 | `tests/e2e/test_experts_karma_pip.py`: owned normal proposal preparation, exact finite ScriptedLLM provider-port wiring, real submission/acceptance,8,700/Hana v3 and local decision-mail companion. The core server has no live provider and does not claim this lane. |
| UAT-18-04 | `tests/e2e/test_karma_copy.py`: independent positively owned baseline restores for Maria/Bob/Mike, real clipboard and exact award differences. Core readiness deliberately has no general reset. |

Those existing pytest files currently use function-local ORM/live-server fixtures.
Running them unchanged still proves a local runner, even with a remote URL option.
Staging Saga must reuse their literal actions/oracles against the actual owned
server and positively guarded companion state. Only the model provider may use
the declared finite ScriptedLLM seam. This supplies wiring evidence, not a claim
about live model quality. Full Saga and visual acceptance retain their own verdict.

## Evidence and cleanup

Transport uses only the existing EB S3 bucket under `experts-uat/<random nonce>/`.
It sends no bearer URLs or AWS keys to the app. The host role must actually prove
S3 read/write in this owned prefix before any image pull or app/DB creation; no
IAM policy or bucket is added. Evidence objects use SSE. Only the exact bundle,
probe and evidence keys for this invocation are deleted after verified download.
No backup prefixes are accessed.

The Actions artifact `experts-idle-readiness-<run ID>` retains public source/build
metadata, actual host/SSM results and the hash-verified original browser evidence
archive. Exports allow only declared regular artifact files and exclude runtime
environment files, TLS keys, PostgreSQL data and Docker login configuration.

Core readiness is a temporary rehearsal. A workload deadline leaves cleanup
reserve; exact ownership labels are checked before removing only this invocation's
containers/networks. A second independent SSM command reconciles owned resources
after any result. Host private files disappear after verified cleanup. If actual
transport or cleanup fails, the run fails and retained owned state is reported;
no staging/UAT pass is inferred. The later complete Saga run determines the final
staging/test-database acceptance and does not continue to production.
