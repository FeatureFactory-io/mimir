# Experts replay: consolidated implementation contract

Status: active local implementation. All 49 dedicated planning workers returned.
Denis declined GitHub publication, then explicitly approved “GO — build using
the local contract”. The current iteration manifest and execution journal record
activation and actual node results; remote publication requirements are waived
by that decision. Main merge/release and production promotion retain human review.

## Scope and acceptance sources

The original 49 acceptance IDs are one iteration, as Denis requested. Their
authoritative paths, line numbers and expanded example counts are in
`docs/experts-replay/scenario-index.json`. There are 43 server acceptance
contracts (83 expanded cases), six browser interaction acceptance contracts,
five additional browser journey/viewport contracts, and four manual UAT
contracts. The eleven browser contracts expand to 23 cases. These are 58 unique
contracts; relocation between layers did not remove or duplicate a requirement.

The six interaction contracts live in `tests/e2e/experts-interactions.feature`.
They require actual clipboard operations, text expansion, hover/focus or visual
truncation. Django-client tests certify their initial HTML, permissions and
receipt arithmetic separately. They cannot certify the interaction. Experts
navigation lives in `docs/features/act-0-auth/experts-navigation.feature`, with
its own Cedar background, independent of the malformed legacy navigation prose.

The approved prototypes remain the frontend source. Graduate the actual Django
templates through BPE; preserve Bootstrap, typography, colors, selectors and the
seven IA viewports. No substitute application images or new design system.

## Story, data and public evidence

Noor Ibrahim asks Elena Svensson on Monday, 23 November, at 09:10 for a Cedarbank
onboarding RFP contributor nomination by Tuesday noon. Elena's job is to find a
relevant Design contributor, inspect public evidence and identify a contact
destination. Rank supports this decision; the application cannot establish
availability or send the nomination. The nomination is an external evidence
record containing candidate, example, reason and next contact action.

The independent source is `test-data/experts/cedar-rfp-01.json`. Design returns
Sofia Reed, Maria Rodriguez, Priya Nair, Daniel Ortiz and Hana Kim, in that order.
Theo is sixth. Mike Chen's 12,450 overall points do not qualify him for Design;
his primary category is Development. Nora's zero score does not qualify her for
a public expert page. Missing and ineligible pages have the same generic 404.

Maria starts at 8,200: released playbooks 5,000, accepted PIP contributions
1,600, consumption 1,200 and learning 400. Her Design score is 7,200. Her public
Accessibility Audit example is playbook 6101. Hana's playbook 6106 is already
version 2 from Maria's historical ADD and ALTER contributions. Mike's 6201 is
also version 2, with workflow 6202 and activity 6203. Import real historical
PIPs, changes and publication receipts rather than replaying live award hooks.

Historical counts do not imply that every source still has a current public
playbook. Keep unknown historical content snapshots null. Bind known released
books to `first_release:<actual_pk>` and preserve their real history. Do not
invent current books, titles or public evidence to balance historical counts.

Mike's 470 author-consumption events include exactly 47 attributed GUI copies.
The remaining historical events are unclassified. His numeric fallback is
`2 released playbooks · 47 copies`. His baseline summary is JSON null, normalized
to empty text. A GUI copy count cannot be inferred from all consumption awards.

Bob has no account. His public page can show evidence; it contains no email or
mailto destination. Contact explains: “You need to be logged in to reach out to
the expert”. Authenticated Elena may inspect Maria's fictional contact URL. No
real message is sent. Private pricing/staffing/PIP/token sentinels remain private.

## Ownership and stable interfaces

| Owner | Responsibility | Consumers |
|---|---|---|
| S03 | KarmaAward/ExpertProfile schema, Cedar adapter, numeric projections, category resolver, shared text/HTML helpers, base list delivery, parent gate/catalog registration | All scenarios |
| S17 | Allowlisted public detail DTO, evidence query and detail delivery | S04/S14/S18–S22 |
| S14 | Request-local contact context and shared contact partial | List/detail; S15/S16 |
| S04 | Card presenter and list graduation | List interaction/journey checks |
| S10 | Existing own-profile contribution UI and one expansion controller | S11/S12/S24/S28 |
| S30 | Sole live ledger writer and first-release transaction integration | S31/S32/S36/S45 |
| S27 | Public evidence, layered prompt, validation and read-only completion boundary | S23 |
| S23 | Provider composition, interaction metadata, summary storage and existing Galdr lifecycle integration | S24–S29; full submission UAT |
| S36 | Successful-consumption service and CSRF GUI receipt | GUI/MCP/export |
| S39 | Token receipt, both existing MCP detail surfaces and shared real MCP test infrastructure | S40–S44/S46 |
| S42 | Completed-export receipts and shared pure filesystem guard | S43/S44/S46 |
| S45 | Full-event replay comparison, race recovery and atomicity helpers | Existing S30 writer |

`CedarDataset` is one frozen container of real ORM objects, including
`users_by_username`, `playbooks_by_pk`, workflow/activity/PIP maps and the oracle.
It provides compatibility ID accessors. Root fixture `cedar_dataset` loads once;
`cedar_baseline` is an alias consuming that fixture. MCP transactional setup must
reuse that importer under its own actual test lifecycle, without double loading.
The loader validates effective runner-owned DB or verified demo ownership before
any write. Never seed the tracked shared seed, ambient development DB, idle or
production. Reuse real email-verification state for functional browser login.

`ExpertProjection` contains user ID, username, display name, total points, primary
category, category/source tuple pairs, public released-book count and successful
GUI-copy count. It contains neither account email nor summary prose. The four
source display buckets are Released/PIP/Consumption/Learning. Public detail uses
`person: PublicExpertDetail`; contact remains a separate request-local value.
Public evidence explicitly requires both public visibility and released status.
General `can_view` permission is broader and cannot replace that filter.

Legacy compatibility found during S03 DoD: the real shared seed includes drafts
with a blank category, and the existing release flow preserves that value.
Unsupported current-book categories must not enter primary-category tie inputs.
Keep explicit resolver/award validation strict, count distinct recognized private
releases for valid ties, and preserve the independent count of all currently
public released authored playbooks. A legacy book must not turn a valid positive
contributor's leaderboard into HTTP 500. The real-DB regression belongs to S03.

S30 first-publication precondition: an otherwise award-eligible draft must have
a recognized playbook category before release/version/award persistence. Reject
blank/retired categories with the existing Django ValidationError convention and
a clear instruction to choose a valid category; the existing release view handles
that exception. Leave the draft and ledger unchanged. Already released or
historical legacy records keep later-release behavior without award backfill.
Do not infer a category or silently omit the first-release award for an eligible
publication. This enforces the approved ledger boundary while preserving reads
of real legacy history.

`expert_text.py` supplies four pure functions: `format_karma`, `category_label`,
`display_initials`, and `format_numeric_fallback`. Card, own-profile and detail
presenters share these; detail must not depend on cards. A zero-score own profile
uses a neutral category display. `experts_html.py` uses Django's existing HTML
parser, list-of-pairs attributes and traversal including the root. S12 appends
the shared source-row assertion used by S18.

S03 also reserves the shared `experts/_breakdown.html` presentation component;
own-profile and public-detail graduation consume that component. The shared
`tests/support/experts_logs.py` context enables actual named loggers and restores
their original configuration, without replacing production logging.

## Ledger and transaction contract

Awards have recipient CASCADE, immutable optional integer content/change/entity
snapshots, event identity, source kind, explicit channel, positive points,
category and original aware event time. Channels are `historical`, `release`,
`accepted_change`, `gui_copy`, `mcp_detail`, and `export`. There is no competing
`pip_decision` alias. Sources are release/major/minor/consumption/learning.

Schema constraints protect event+recipient uniqueness, one known first release
per playbook independent of recipient, a single live non-consumption anchor,
positive values, paired entity snapshots and valid source/channel combinations.
Unknown historical release references are valid. S30's
`persist_awards(tuple[AwardSpec], correlation_id=...)` returns immutable
`tuple[AwardOutcome, ...]`; each outcome has award, created and reason.

Consumption uses `consumption:<channel>:<authenticated_actor_pk>:<action_uuid>`.
Entity type/ID are comparison payload, not key components. The same action key
must match the entire original logical recipient set, target, author, category,
source and points. Preserve the stored original time on replay. Changed payload
conflicts; a partial existing pair is an error, never silently repaired. Another
legitimate actor/channel may independently use the same UUID.

Validate the complete event before inserting. Insert both consumption/learning
awards atomically. Recover only recognized uniqueness races after leaving the
failed savepoint. Retry SQLite busy failures only after rolling back the whole
owned transaction; caller-owned atomic transactions propagate the failure.

First release earns 5,000 once. Later publication earns no second release award.
Accepted ADD Activity/Skill/Artifact earns 500; the twenty supported minor changes
earn 100. Submission/rejection/unsupported changes earn zero. Accepted-change
awards use `accepted_change:<change_pk>`, channel `accepted_change`, original
decision time, and the existing finalization transaction. Do not bump the version
twice. Preserve normal notification content; no invented earnings email.

Successful authorized consumption earns five for author and consumer. Guest or
self consumption earns zero. For PIPs, self includes creator OR target playbook
author. Existing creator-or-staff PIP permission stays intact. Mike is already
staff; an eligible read of Maria's Design PIP credits Mike and Hana, not Maria.

The GUI endpoint derives actor from the authenticated request and accepts only
entity type/ID and UUID, under CSRF. A clipboard failure posts no success receipt.
If copying succeeds but the receipt fails, preserve the copied text and retry
only the receipt with the same UUID.

## MCP and export boundaries

Keep both actual existing MCP entrypoints. Nine detail tools fetch and completely
serialize authorized content before posting an explicit receipt. Ordinary REST
GETs, collection listings and imports remain award-free. The token endpoint
accepts only the trusted `mcp_detail`/`export` channel allowlist and derives actor
from token authentication. Reject actor/recipient/points/category/time overrides.

Shared test support belongs to S39 in `tests/support/karma_mcp.py`. Its factory
requires explicit actor and entrypoint, connects the real registered FastMCP
client, real HTTP and real DB, and restores ContextVar/client/configuration/env
state on every exit. It owns and closes only clients it creates. Async ORM and
relation-backed phase/PIP serialization use `sync_to_async`.

Strict in-process proofs clear the existing unsafe-ORM flag AFTER importing the
actual legacy registration. Existing legacy startup compatibility remains intact.
Actual stdio startup proves protocol/content/awards, separately from strict async
safety. Temporary subprocess DBs/settings/mail are test-owned; no ambient demo DB.
Bounded context/phase log changes replace existing actor-email INFO logs with
identifier-only logs when the feature is implemented.

Export awards happen after every canonical, mirror and ADE output finishes, once
per call irrespective of file count. Failure earns zero. A receipt failure after
files finish reports `files_written=true` and permits receipt-only retry. Both
entrypoints reuse the pure standard-library guard in
`mcp_integration/facade/export_paths.py`, which is included by Dockerfile.mcp.
Preflight every requested output root. Imports reuse existing production paths;
test helpers live in undecorated support modules, never imported test modules.

## Summary and model boundary

`ExpertProfile.contribution_summary` is the canonical stored field. S27's
`PublicContributionSummaryBoundary.complete(subject_id, llm=..., correlation_id=...)`
is read-only and returns text, normalized `LLMResponse` and body-free trace events.
Safe typed failures retain available response/trace. S23 delegates once, appends
the storage event and persists success or failure metadata without acquiring
award capability. `AgentInteraction` stores call ID, subject/PIP reference,
correlation, model, usage, latency, cost, outcome and safe trace, never model bodies.

The single server-only `CONTRIBUTION_SUMMARY_LLM` composition setting defaults to
None. Capture the chosen port before dispatch. The optional BaseLLM bridge reuses
normal Galdr assessment parsing/policy; uninjected legacy behavior stays intact.
One submission consumes summary then assessment: two finite scripted turns.
Withdrawal-to-draft and resubmission consume four. Pre-provider failures consume
zero turns; a provider attempt consumes one. Never synthesize a successful reply.

Normalize a received SDK response even when text is empty/truncated; preserve
known usage and stop reason. S27 rejects invalid public prose. The separate
legacy private assessment bridge rejects truncated assessment output. Transport
failure has unknown usage/cost, represented as null. Safe failure codes include
`provider_failed` and `output_validation_failed`; no raw exception/body leakage.
Last good text and timestamp survive refresh failure.

Submission does not publish a draft PIP title/body even when its target is public.
Only current public released evidence and accepted changes with matching
publication receipts enter the public prompt. Prose excludes mutable scores and
rank. GET, copy and award changes never call the model. ScriptedLLM exposes one
`calls` tuple, capturing an attempted request before exhaustion. S27's PRF-03
`happy.json` is one call; S23's `submission_happy.json` is two calls.

## Verification and shared registration

Parent merges all named Make gates and catalogs once into S03 structural wiring.
Subsequent scenarios do not all edit these files. A single parameterized exact
acceptance runner selects each of the 43 real server contracts, parses actual
Behave JSON and requires the declared expanded count with no skipped/undefined
steps. Never create a copied acceptance-spec tree or scan unrelated malformed
legacy features. Browser-backed contracts have separately named server checks.

All node gates are pytest or make. Every graph has a backend node and terminal
DoD node; DoD conjunctively runs relevant backend, exact acceptance, browser,
log-story and agent-proof gates. Protocol checks are backend/acceptance nodes,
not mislabeled browser certification. Missing/zero/skipped selection fails.

The aggregate Experts acceptance gate covers downstream S46, which consumes
S45. It therefore remains a mandatory iteration-final gate after all49, rather
than a circular prerequisite to S45's own completion. Global `make lint` is also
retained at iteration-final DoD and its actual outcome must be recorded; scoped
lint cannot establish it. The harness health gate can run at either stage.
Before final aggregate AT, remove WIP only from completely certified owning
feature files and require all83expanded server cases without selected skips or
undefined steps. This scheduling correction waives no verification obligation.

The aggregate `make test-agent-experts` also remains mandatory at iteration-final
DoD. It selects later S28/S29 proof bodies, so it is scheduled after those nodes,
rather than used as S24's stored-read acceptance gate. S24 still requires its
complete complementary server and seven-viewport browser checks plus harness;
no pending agent proof is counted as passed or removed from the iteration.

S05's narrow list-to-Maria browser case alone cannot close its composed scope.
The manifest adds a separate fresh N3a and mandatory browser gate for the full
CEDAR-JOURNEY-01/UAT-18-01 nomination, before independent N4. It uses a new
test-only file and the already approved route/data/contact policy; no product
screen or feature is added. Record actual elapsed time and nomination evidence
as an automated UAT path, keeping later deployed Saga and human review distinct.

Backend and browser checks run in separate processes/settings. Browser command:

```text
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio <specific test paths> -x
```

Reuse the repaired existing function-scoped server fixture and real login helper.
Log capture must temporarily enable and restore actual loggers disabled by test
settings; changing caplog's level alone does not enable them. No integration
domain/HTTP doubles. ScriptedLLM is the sole model seam in agent proofs.

One owner registers each Behave phrase. Share undecorated helpers, never import
decorated step modules. S32 owns a single parameterized operation/entity action
for both major and minor matrices. S33 supplies only its minor setup helper.
S41 owns the Maria/Mike unchanged-total phrase reused by S44. S28's no-extra-call
acceptance keeps the actual captured port through generation and subsequent
receipt/GET; another proof's catalog link is insufficient evidence.

## Composed journey and UAT placement

| Contract | Owner and complete observation |
|---|---|
| CEDAR-JOURNEY-01 | S05: Design → Sofia → Design → Maria → actual playbook/workflow → profile → mailto destination → external nomination record, availability unconfirmed |
| CEDAR-JOURNEY-02 | S16: anonymous list → Maria → public evidence → actual keyboard contact explanation → private-data exclusion |
| CEDAR-JOURNEY-03 | S28: own-profile expansion/source reconciliation → real copy → 8,205 with unchanged prose |
| EXPERTS-LIST-10 | S04: baseline rank and both actions at every one of seven IA viewports, plus long/missing state matrix |
| EXPERTS-VIEW-07 | S17 body/rail base; S16 composed contact/evidence at seven viewports, rail stacks below 768 |
| UAT-18-01 | S05: actual nomination, measured time, fixture hash, commit and viewport; proposed five-minute target is measured, never forced |
| UAT-18-02 | S16: guest explanation/evidence/privacy, Other empty state and missing/Nora 404 |
| UAT-18-03 | S32: actual UI profile 8,200, four sources, keyboard expansion; normal submission refresh earns zero; staff accepts ADD, +500, Hana v3; local decision-mail companion |
| UAT-18-04 | S38: independent baseline restores for Maria, Bob and Mike clipboard lanes and exact award differences |

MIN repeats final Saga certification before merge. Automated/operator runs are
labeled as such, with no fabricated human usability claim. The literal human
visual review receives an actual gallery at the merge/release review gate.

## Structural application and delivery gates

PIN applies scenarios sequentially, preserving every existing working body.
New methods and test bodies raise NotImplementedError; new routes remain
unregistered and new templates contain comments. Complete declarative model
fields/constraints and real generated DDL are architecture structure. S03/S23
apply their empty schema only to the replay-owned tracked seed and commit it
with each migration. No Cedar rows, award hooks, fixture implementation or
passing test bodies are introduced. Never fake an applied zero-operation schema.

Record the actual files and commit for every scenario. Construct the conflict
map and parallel groups from those real commits, then publish self-contained
PIN-04 issues with A–H, graphs, Lessons Learned and the docs handoff SHA. Only
then present PIN-05 for Denis's GO. GO authorizes the reviewed implementation
contract; main merge, release and production promotion retain their later human
review gates. Capture real failures, fixes and changes to this contract in the
storyboard, with genuine CLI recordings and native Cursor screenshots. Narration
uses a male voice.


## Summary lifecycle logging ownership clarification

S23 E4/E5 are emitted by the existing S27 public completion boundary before the
provider attempt; E1 belongs to the scheduler and E2/E3/E6–E10 to the summary
service. The boundary adds only actual body-free evidence length/public IDs and
accepted sentence-count metadata to its existing typed trace. S23 consumes those
values after completion; it does not recreate pre-provider beats afterward. This
clarifies ownership within the existing contract without a callback/observer API,
evidence requery, extra model turn or changed public signature. S27’s original
owner performs the bounded follow-up under Denis’s continuing instruction.
