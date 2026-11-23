# S14: EXPERTS-REACH-01 Give authenticated Elena the correct contact destination

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S14
acceptance_id: EXPERTS-REACH-01
feature_file_path: docs/features/act-18-experts/experts-reach-out.feature
feature_line: 8
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S17
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 75ccd99b9e8cc7cab8e7c84fc1d4edf3ce411491e6ac6866c5c26326ef0790ec
```

## A — Context map


| Verified reference | Purpose |
|---|---|
| `docs/features/act-18-experts/experts-reach-out.feature:8–27` | Exact authenticated destination and both guest restrictions. |
| `templates/mockups/experts/_reach_out.html:1–9` | Approved shared action, stable selector, focusable disabled-button wrapper and explanation. |
| `docs/architecture/SAO.md:3883–3914` | Authenticated mailto handoff, existing Bootstrap components, real AT/browser verification. |
| `docs/ux/IA_guidelines.md:1160–1192` | List/detail action clusters, keyboard explanation and selector contracts. |
| `templates/base.html:345–355` | Existing Bootstrap bundle and DOMContentLoaded tooltip initialization; no new tooltip framework needed. |

Additional inspected sources: Act18 journey, Cedar JSON, prototype views/list/detail, E2E feature and actual `page`/`live_server_url` fixtures, existing `login` helper, AT catalog/environment, log-story helper and execution-graph schema.

S03 owns ranking/schema/Cedar/public list. S17 owns eligible public detail projection and route. Neither public projection should acquire email fields.

## B — Do-not-do list


- Do not send mail, call EmailService, add a provider, queue or contact endpoint.
- Do not add availability, suitability, appointment or messaging promises.
- Do not use prototype `guest=1`, fictional shell users or a template-provided authentication boolean for authorization.
- Do not fetch target emails before checking the actual request’s authenticated user.
- Do not add email to cached/shared public list/detail projections.
- Do not duplicate list/detail querying, evidence filtering or eligibility logic.
- Do not rewrite existing account editing, routing, permissions or summary behavior.
- Do not log email addresses, mailto destinations, request query strings or message bodies.
- Do not treat a missing/invalid email as a working handoff.
- Do not implement behavior during PIN skeleton application.

## C — Governing SAO sections


- **Experts & Karma delivery architecture — planned delta**
- **Public discovery and profile projection**
- **Web delivery and notification reuse**
- **Test strategy for this delta**
- Existing anonymous-read/no-serializer-leaks rules.

The request-scoped contact mapping supplements successfully projected public experts. It is never returned by the public query service or stored on a model.

## D — Tests and implementation slices


### Boundary and behavior

One builder accepts a real `HttpRequest` and usernames obtained from S03/S17’s eligible public projections. It returns immutable, request-local contact values:

- Authenticated, valid Maria address: `href == "mailto:maria.rodriguez@example.com"`, state `available`.
- Anonymous request: state `authentication_required`, no href; return before any target-email query.
- Authenticated target with absent/blank/invalid address, CR/LF, or mailto-header injection: state `unavailable`, no href. Use the neutral explanation **“Contact information is unavailable”**. This is defensive handling, not a new messaging flow.
- Validate a single mailbox using Django’s email validator. Encode mailbox characters for a mailto URI while retaining Maria’s exact expected destination; never append subject/body/header parameters.
- Both views use one `_with_expert_contacts` helper after their existing public projection succeeds. The helper copies public dictionaries and adds a transient `contact` value; it does not mutate the original projection.
- The shared partial consumes `person.contact`, never `person.email` or `mock_authenticated`.
- Guest wrapper retains the exact existing explanation, tabindex, `aria-describedby` and Bootstrap tooltip recipe. S15/S16 subsequently certify pointer/focus behavior.

### Assertions

| Test | Required assertions |
|---|---|
| `test_build_expert_contact_context_with_authenticated_request_returns_exact_mailto` | Real Cedar Elena/Maria; exact href; immutable values/mapping; public projection unchanged. |
| `test_build_expert_contact_context_with_guest_request_does_not_query_email` | Real anonymous request; zero target-email queries; href absent; exact sign-in explanation; query parameters cannot enable contact. |
| `test_build_expert_contact_context_with_unusable_email_disables_handoff` | Real DB updates for blank, malformed, CR/LF and header-injection inputs; no clickable destination, neutral unavailable explanation. |
| `test_build_expert_contact_context_with_invalid_boundary_input_raises` | Non-HttpRequest, missing authentication middleware user, scalar-string username collection, empty/invalid usernames reject clearly; empty valid sequence returns empty mapping. |
| `test_reach_out_with_authenticated_elena_matches_both_surfaces` | Real client login; GET list/design and public detail; scoped Maria anchors have the exact href and named action; no availability claim; no locmem outbox growth. |
| `test_reach_out_with_guest_request_excludes_email_on_both_surfaces` | GET both routes anonymously; no target email anywhere in response/context contact values or mailto; disabled action; public content still renders. This supplies baseline safety, leaving interaction certification to S15/S16. |
| `test_reach_out_with_authenticated_unusable_email_renders_disabled_action` | Both routes remain 200; no malformed destination or 500; neutral unavailable explanation. |
| `test_reach_out_log_story_happy` | All successful builder beats through `assert_log_story`; actor ID/count/state, no raw address/href. |
| `test_reach_out_log_story_reject` | Anonymous and unusable-email branches; no raw address/href, no synthetic exception for ordinary unavailability. |
| `test_reach_out_with_authenticated_browser_exposes_exact_destination` | Existing real `page` and `live_server_url`; standard login with Cedar password; both surfaces expose exact href by semantic/test-id selectors; inspect href without launching external mail software; no availability promise. |

Reuse `load_cedar_baseline()` and `CEDAR_PASSWORD` from S03. AT uses `context.cedar_dataset`; no second fixture adapter. Reuse S03’s baseline phrase and S01’s `Elena is authenticated` binding.

S14 owns only three new AT bindings:

1. `When she inspects Maria's Reach out action on list and public detail`
2. `Then both destinations are "{destination}"`
3. `Then the action does not imply that availability is confirmed`

They request actual production URLs using the real Django client and inspect Maria’s rendered action, not fixture-derived expected HTML.

### Gates



The proposed Make target uses the existing acceptance settings and real runner:

```text
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^EXPERTS-REACH-01 ' docs/features/act-18-experts/experts-reach-out.feature
```

This deliberately selects the exact named contract while feature-level `@wip` remains. Require one executed/passed scenario; zero selection is not completion. The aggregate Experts target stays incomplete until all contracts run.

### BPE-02 through BPE-05

1. **BPE-02:** Red boundary tests, implement request-scoped contact builder, integrate helper into S03/S17 views, prove log story in the same behavior commit.
2. **BPE-03:** Graduate shared partial and wire both production templates. Preserve prototype action classes, accessibility and hooks.
3. **BPE-04:** Implement the three owned AT bindings, catalog entries and exact scoped Make target; run real contract.
4. **BPE-05:** Implement browser destination proof using existing fixtures and login; inspect destinations without opening a mail application.
5. **BPE-06:** Run rollup and log gates; check privacy, no-send boundary and partial reuse.

After PIN-04 issue creation and PIN-05 GO: initial docs handoff commit cites `Refs #N`; each slice commit cites `Refs #N` and receives the required issue update with SHA and next slice. Final passing slice uses `Closes #N`. PIN owns combined approval/publication; this worker proposes no posting.

## E — Log story


Where: `expert_contact_context.build_expert_contact_context`.

| Beat | Trigger | Must include |
|---|---|---|
| entry | Valid request starts | `entry`, `actor_id=`, `target_count=` |
| branch | Anonymous request | `branch`, `reason=authentication_required`, `email_lookup=false` |
| processing | Authenticated batch lookup | `processing`, `email_lookup=true`, `target_count=` |
| branch | Missing/unusable address | `branch`, `reason=contact_unavailable`, `unavailable_count=` |
| exit | Mapping ready | `exit`, `available_count=`, `disabled_count=` |
| validation | Invalid boundary input | `validation`, `reason=invalid_input`, `field=` |

INFO for ordinary flow; WARNING for invalid boundary input. Include a request/correlation identifier when already supplied by middleware, without introducing infrastructure. Use actor primary key or `anonymous`, never email. No raw username/email/href is necessary.

Happy/reject caplog tests assert individual beats using `tests/support/log_story.py::assert_log_story`, and explicitly assert address/href absence.

## F — MCP tools


Not applicable. This is server-rendered request-specific web contact presentation. No MCP tool, facade registration or API mutation.

## G — Agent proofs


Not applicable. S14 does not invoke or alter the SAO §17 contribution-summary agent, model boundary, control trace or PRF rows. No ScriptedLLM fixture or agent-proof gate belongs here.

## H — Mockup graduation


| Source | Destination | Strategy |
|---|---|---|
| `templates/mockups/experts/_reach_out.html` | `templates/experts/_reach_out.html` | `rewire`: actual request-derived contact state replaces mock auth/email data. |
| `templates/mockups/experts/list.html` action include | `templates/experts/list.html` | `partial`: S03 owns list recipe; S14 adds shared partial include. |
| `templates/mockups/experts/detail.html` action include | `templates/experts/detail.html` | `partial`: S17 owns detail recipe; S14 adds shared partial include. |

Retain `experts-reach-out-<username>` for authenticated anchors and the prototype guest-wrapper hook, scoped within the relevant card where repeated. Retain focusable wrapper, disabled button, exact sign-in explanation and existing Bootstrap initialization. No base-template or JavaScript change is currently needed. S15/S16 own focused browser certification of the guest tooltip.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-reach-out.feature:8`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-REACH-01
  nodes:
  - id: N1-contact-context
    title: Authenticated request contact boundary
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/expert_views.py
    - methodology/services/expert_contact_context.py
    - tests/integration/test_experts_reach_out.py
    - tests/unit/test_expert_contact_context.py
    tests:
    - test_build_expert_contact_context_with_authenticated_request_returns_exact_mailto
    - test_build_expert_contact_context_with_guest_request_does_not_query_email
    - test_build_expert_contact_context_with_unusable_email_disables_handoff
    - test_build_expert_contact_context_with_invalid_boundary_input_raises
    - test_reach_out_log_story_happy
    - test_reach_out_log_story_reject
    log_story_rows:
    - expert_contact_context.build_expert_contact_context:entry
    - expert_contact_context.build_expert_contact_context:branch
    - expert_contact_context.build_expert_contact_context:processing
    - expert_contact_context.build_expert_contact_context:exit
    - expert_contact_context.build_expert_contact_context:validation
    gate:
      command: pytest tests/unit/test_expert_contact_context.py tests/integration/test_experts_reach_out.py -k 'contact_context
        or log_story' -x
      log_story_command: pytest tests/integration/test_experts_reach_out.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  - id: N2-shared-action
    title: Graduate and wire one contact partial
    bpe: BPE-03
    depends_on:
    - N1-contact-context
    footprint:
    - templates/experts/_reach_out.html
    - templates/experts/detail.html
    - templates/experts/list.html
    - tests/integration/test_experts_reach_out.py
    mockup_source: templates/mockups/experts/_reach_out.html
    production_template: templates/experts/_reach_out.html
    graduate_strategy: rewire
    tests:
    - test_reach_out_with_authenticated_elena_matches_both_surfaces
    - test_reach_out_with_guest_request_excludes_email_on_both_surfaces
    - test_reach_out_with_authenticated_unusable_email_renders_disabled_action
    gate:
      command: pytest tests/integration/test_experts_reach_out.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N3-exact-acceptance
    title: Bind authenticated contact acceptance contract
    bpe: BPE-04
    depends_on:
    - N2-shared-action
    footprint:
    - docs/features/steps/experts_reach_out_steps.py
    gate:
      command: make test-experts-s14-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N4-browser-handoff
    title: Certify actual browser destinations without sending
    bpe: BPE-05
    depends_on:
    - N3-exact-acceptance
    footprint:
    - tests/e2e/test_experts_reach_out.py
    gate:
      command: make test-experts-s14-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N5-definition-of-done
    title: Verify authenticated handoff and disclosure boundary
    bpe: BPE-06
    depends_on:
    - N4-browser-handoff
    footprint:
    - tests/e2e/test_experts_reach_out.py
    - tests/integration/test_experts_reach_out.py
    - tests/unit/test_expert_contact_context.py
    gate:
      command: make test-experts-s14
      log_story_command: pytest tests/integration/test_experts_reach_out.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  scenario_dependencies:
  - S03
  - S17
```

## Lessons Learned

- The prototype’s `mock_authenticated` and email-bearing fixture dictionary are design conveniences; graduating them unchanged would weaken the authorization boundary.
- A separate request-local contact mapping preserves public projections and supports both routes through one implementation.
- Existing Bootstrap initialization already supports the approved guest-wrapper recipe; new tooltip JavaScript is unnecessary.
- The actual browser fixtures are `page` and `live_server_url`; browser pytest gates must override global `addopts`.
- Cedar is domain data, not a loaddata fixture. Reuse S03’s real adapter and shared password; do not replay historical award hooks.
- Missing target mailboxes need a disabled, honest state, without turning an email handoff into a messaging feature.

## Structural application evidence

`docs/experts-replay/pin-evidence/S14.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
