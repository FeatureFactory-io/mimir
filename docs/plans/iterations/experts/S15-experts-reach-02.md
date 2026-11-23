# S15: EXPERTS-REACH-02 Explain guest contact restriction on the list

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S15
acceptance_id: EXPERTS-REACH-02
feature_file_path: tests/e2e/experts-interactions.feature
feature_line: 21
primary_execution_layer: e2e
expanded_case_count: 1
dependencies:
- S04
- S07
- S14
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 39ad6ab4fdaa2e310012dcd62838000bd64b49fcfa42999409399cfe1b0b2028
```

## A — Verified context


| File:lines | Implementer context |
|---|---|
| `docs/features/act-18-experts/experts-reach-out.feature:14-20` | Exact contract: anonymous Bob, Design list, disabled contact, exact explanation, actual hover/focus, available profile action. |
| `templates/mockups/experts/_reach_out.html:5-8` | Existing recipe: focusable wrapper, Bootstrap tooltip, disabled native button and visually hidden description. |
| `mockups/experts_views.py:61-83` | Prototype authentication uses a fabricated actor and `guest=1`; production certification must use a genuinely anonymous session. |
| `templates/base.html:350-356` | Shared shell initializes Bootstrap Tooltip on `DOMContentLoaded`; reuse this initialization. |
| `tests/e2e/conftest.py:101-117,141-168` | Existing function-scoped context/page and selectable function-scoped live server; actual fixture names are `page` and `live_server_url`. |

Also inspected: replay `AGENTS.md`, `CLAUDE.md`, orient roster, live PIN/BPE rules, ownership guidance, Cedar job/data, IA, actual prototype list and view bodies, harness/catalog, settings and graph schema. Current production Experts implementation and Cedar ORM adapter are absent; upstream S03/S14 supply them.

Cedar Bob has no username/email/account. Maria is `mrodriguez`; her test-only email is `maria.rodriguez@example.com`.

## B — Do not do


- Do not alter production list/query/contact behavior; S03 owns list delivery, S14 owns request-local contact projection and shared production partial.
- Do not duplicate S03’s `he opens "{path}"` or S07’s anonymous-Bob bindings.
- Do not use prototype `guest=1`, fabricated authentication or prototype data projection as production evidence.
- Do not implement an HTML check and call it proof of actual hover or keyboard interaction.
- Do not send email, invoke a mail client, add messaging or infer availability.
- Do not add a parser: use `tests/support/experts_html.py` helpers `find_by_test_id`, `element_text`, `_walk_elements`.
- Do not modify shared browser lifecycles, create Bob’s account, change the seed or add migrations.
- Do not remove feature-level WIP for unrelated contracts, exclude S15 from scope or accept zero/skipped tests.

## C — Governing architecture


`docs/architecture/SAO.md`, **Experts & Karma delivery architecture — planned delta / Web delivery and notification reuse** (`3897-3906`): Django/templates, shared Bootstrap shell, production `/experts/`, authenticated mailto and no automatic send.

**Test strategy for this delta** (`3912-3928`): real DB/client AT, separate actual-browser focus/geometry, no skipped/empty completion evidence.

`docs/ux/IA_guidelines.md` **§11**, especially `1182-1185`: no guest email-bearing href; exact explanation through `aria-describedby`, pointer hover and keyboard focus. Seven required viewports appear at `1194-1203`.

SAO §17 summary generation is unaffected. No new agent capability, provider path or MCP interface applies.

## D — Tests and exact assertions


**Verification-layer correction:** preserve the original acceptance contract unchanged. Map **full `EXPERTS-REACH-02` to the browser test** in the catalog. Separately name initial-markup Django-client coverage **server-contract AT**. Do not register a fake browser-interaction Behave binding. This retains S15 in the confirmed 49-contract scope.

| Test | Assertions |
|---|---|
| `test_guest_list_contact_with_anonymous_request_restricts_contact` | Real Cedar DB; anonymous client GET `/experts/?category=design` returns 200 without login redirect. Within Maria’s card, native Reach out button is disabled; wrapper is keyboard-focusable; associated description has exact text; Bootstrap tooltip trigger is declared. No mailto destination in wrapper/ancestors/descendants; no Cedar contact emails anywhere in response HTML. View profile remains an enabled named link with `/experts/mrodriguez/`. |
| `test_guest_list_contact_with_authenticated_then_guest_requests_does_not_leak_email` | Same client first authenticates Elena and observes Maria’s correct contact destination; logout then request Design list. Guest markup again satisfies the shared restriction assertion, contains no contact email/mailto and has an anonymous request user. Detects cached/authentication-independent contact leakage. |
| `test_experts_reach_02_with_guest_activation_explains_restriction` | Full exact contract, parameterized over seven IA viewports × `hover`/`keyboard` = 14 cases. Real anonymous context; production route; Maria visible; contact disabled/inert; no email/mailto in rendered DOM; View profile enabled with correct destination. Pointer hover or actual Tab traversal reaches wrapper and displays exact explanation. Assert wrapper’s description relation resolves correctly after Bootstrap updates it. Visible tooltip bounds are inside viewport; document has no horizontal overflow. |

Keyboard proof uses actual `page.keyboard.press("Tab")`, bounded traversal and a focused-wrapper assertion; direct `locator.focus()` is insufficient. Profile link is checked without following detail, avoiding an S17 dependency.

The original phone defect was **tooltip clipping despite passing page-overflow checks** (`docs/plans/act-18-experts-esm-handoff.md:40-42`); therefore tooltip geometry is independently required.

Final commands, provided by proposed Make targets:

```text
make test-at-experts-reach-02-server-contract
make test-e2e-experts-reach-02
make test-experts-reach-02
```

Server target executes:

```text
.venv/bin/pytest tests/integration/test_experts_guest_list_contact.py -x
```

Browser target executes separately:

```text
E2E_LIVE_SERVER_SCOPE=function .venv/bin/pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest_list_contact.py -x
```

Expected completion: two server-contract tests and fourteen browser cases pass, none skipped. Do not claim the exact interaction contract from `manage.py behave` or `make test-at-experts`: their Django client cannot execute the interaction. Other genuinely server-only exact Behave gates must explicitly select `@experts` over inherited WIP and reject zero/skips.

## E — Log story


Empty, justified: S15 adds certification only, with no new service/controller/contact branch. Production observability remains owned by S03/S14; do not manufacture duplicate logs. No S15 `log_tests` or `log_story_command`.

## F — MCP


Not applicable. No tool, schema, registration, facade or API change.

## G — Agent proofs


Not applicable. No SAO §17 capability or PRF changes; no ScriptedLLM, ToolExecutor or agent-proof command.

## H — Mockup graduation


S14 graduates `templates/mockups/experts/_reach_out.html` into `templates/experts/_reach_out.html`, replacing fictional authentication and protecting contact payload construction. S03 supplies production list inclusion and profile links. S15 certifies their resulting production UI; no BPE-03 node or production template edit belongs here.

Preserve wrapper focusability, associated exact explanation, Bootstrap hover/focus behavior and native disabled button. Assert tooltip bounds at both phone widths as well as the other five IA profiles.

## Parent convergence

Authoritative acceptance source: `tests/e2e/experts-interactions.feature:21`; 1 expanded case(s), primary layer `e2e`. Dependencies: S04, S07, S14. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.
This entire acceptance contract is browser-certified. Server checks are complementary initial-HTML/receipt contracts; no clipboard/hover/expansion Behave substitution is allowed.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-REACH-02
  nodes:
  - id: S15-N1-server-contract
    title: Certify upstream guest contact HTML and request isolation
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_guest_list_contact.py
    - tests/support/experts_guest_contact.py
    tests:
    - test_guest_list_contact_with_anonymous_request_restricts_contact
    - test_guest_list_contact_with_authenticated_then_guest_requests_does_not_leak_email
    gate:
      command: pytest tests/integration/test_experts_guest_list_contact.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-write-concise-methods
      - do-docstring-format
  - id: S15-N2-acceptance-mapping
    title: Register separate server-contract AT and full browser mapping
    bpe: BPE-04
    depends_on:
    - S15-N1-server-contract
    footprint: []
    gate:
      command: make test-experts-s15-server
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S15-N3-browser-contract
    title: Prove exact guest interaction across seven viewports
    bpe: BPE-05
    depends_on:
    - S15-N2-acceptance-mapping
    footprint:
    - tests/e2e/test_experts_guest_list_contact.py
    - tests/support/experts_guest_browser.py
    gate:
      command: make test-experts-s15-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: S15-N4-done
    title: Require both server and full browser evidence
    bpe: BPE-06
    depends_on:
    - S15-N3-browser-contract
    footprint: []
    gate:
      command: make test-experts-s15
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-follow-commit-convention
      - do-small-increments
      - do-github-issues
  scenario_dependencies:
  - S04
  - S07
  - S14
```

## Lessons Learned

The exact acceptance scenario crosses verification layers: Django-client assertions establish emitted HTML, while actual hover, Tab focus and phone tooltip bounds require a browser. Making that distinction explicit avoids either weakening the contract or importing browser behavior into AT.

Existing prototype evidence identified tooltip clipping that document-overflow checks missed; production certification must retain both checks. No writes, tests, commits, provider calls or emails were performed.
