# Experts replay operator instructions

Read `CLAUDE.md`, the parent Dr Dobbs instructions, `docs/architecture/SAO.md`
and the current feature/IA artifacts before changing production behavior.
Use playbooks in UI language and methodology only in internal code.

This replay executes ESM, then PIN, then BPE inside MIN. The approved storyboard
is a shooting script; record observed results and deviations rather than forcing
the application to match a success claim. Native editor screenshots and actual
CLI cast/transcript files are the selected capture method. Narration is male.

## PIN precedence for this replay

Within PIN-03, BPE-01 supplies the feature plan. PIN owns standalone BPE approval
and GitHub Issue Handoff by heading, including its current Step 8; obsolete
references to skipping Steps 9/10 do not control the gate. Planning workers return
plans and skeleton text without writes. The sequential apply may commit only
structural unimplemented skeletons, without real behavior, filled production
templates or implementation-test logic.

PIN-04 publishes scenario issues with BPE-01 sections A-G, graphs, actual
footprints, Lessons Learned and a docs handoff commit reference. PIN-05 obtains
actual human GO on that concrete contract. BPE-02+ behavior and implementation
tests begin only after those records and GO. Standalone BPE keeps its original
handoff rule. This scoped interpretation does not change the released playbook.

ESM-06 governs mockups under `/mockups/`, DEBUG only, with the shared shell,
banner and inventory. Ignore the stale PIN-01 ESM-04/old-directory reference.

## Local recording environment

The original Mimir working tree is preserved. This clean replay starts at
333c36ded6bf58bdef94049ca0f5bf98c9ce3124. Session setup lives outside the repo at
`/Users/denispetelin/Desktop/RIPL-Experts-Production/`.

Docker images built, but startup stalled for both demo and an unmounted probe.
Only those replay-owned containers were removed. The active ESM process is the
isolated host fallback at http://127.0.0.1:18180 using the package's host-demo.sh.
Its DB is `runs/session-01/data/mimir.db`; mail writes only to `session-01/mail`.
Inspect `runtime-isolation-proof.json` and the ownership manifest before seed or
reset. No Cedar records go into production or idle databases. Re-verify effective
settings whenever configuration changes. Container startup is not marked passed.

## Delivery gates

Follow test-first skeleton/red/green/refactor with real DB integration tests.
AT uses the Django client; journey certification uses Playwright. Reuse the
existing fixture/E2E helpers; track missing catalog/step support as TFK work.
UAT and visual inspection run on the iteration branch before merge. Follow the
repository's drift/escalation rules. Human review remains required for main
merge and release. Production promotion is a separate explicit decision.

## Local execution override authorized by Denis

Denis declined GitHub publication (“No, skip this part”), then explicitly
approved “GO — build using the local contract”. The local
`docs/plans/iterations/ITER-20261123-experts-replay.yaml` replaces the published
milestone as operational ground truth. Do not create GitHub issues/comments.
Use `docs/plans/iterations/experts/execution-journal.md` for commit-linked node
progress and next steps. This explicit user instruction supersedes remote-issue
handoff/traceability requirements for this replay; it does not waive tests,
footprints, fresh node agents or later merge/release review gates.
BPE-02+ implementation and real test bodies are now authorized within that
contract. Record observed results; narration remains male.
