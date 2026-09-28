# FOB-REALM-NAV-SIDEBAR — Implementation Plan

**Feature ref:** FOB-REALM-NAV-SIDEBAR
**Source:** BPE-01 Plan Feature, approved 2026-09-28
**Reconciliation:** `docs/plans/FOB_REALM_NAV_SIDEBAR_CHANGE_RECONCILIATION.md`
**Graph:** `docs/plans/FOB_REALM_NAV_SIDEBAR-feature-execution-graph.yaml`

Graduate `templates/mockups/nav/_shell.html` into production `templates/base.html`. Keep `/mockups/nav/`.

Locked decisions: realm bar (FeatureFactory, Mimir, Huginn, Yggdrasil, Heimdall, same tab) plus session chrome on the right; sidebar sections Workspace / Methodology / Collaborate; seam chevron to width 0; `localStorage` key `mm-sidebar-collapsed`; guests see the full sidebar; Home, Teams, and PIPs still login-redirect. Keep existing `nav-*` testids.

## Dr. Dobbs bounds

Each graph node is one invocation. Do not edit files outside that node's footprint. `build_shell_context(request) -> dict` is stubbed before N1. N1 fills that body only. N2 updates shell assertions and `base.html` together.

## Section A — Context Map

- `templates/base.html` lines 50–180 — entity links inside `main-navbar`; replace with realm links and move entities into the sidebar.
- `templates/mockups/nav/_shell.html` lines 186–310 — `realm-navbar`, `sidebar-toggler`, `sidebar-collapse-toggle`, `app-sidebar`.
- `methodology/context_processors.py` lines 34–88 — `primary_nav_section` picks the active item from the URL. `build_shell_context` adds realm items and guest-vs-auth chrome.
- `static/css/mimir-app.css` around `.mm-browser-panel-toggle` — seam-button geometry for `.mm-sidebar-panel-toggle`.
- `tests/integration/test_base_shell.py` lines 8–54 — asserts `main-navbar` until N2.

## Section B — Do-Not-Do

- No React/SPA. Django templates plus a small inline script for collapse.
- Do not delete mockup templates or `/mockups/nav/` routes.
- Do not change Content Browser panel toggle, entity context rails, or the feedback tab.
- Do not change guest redirect targets for `/dashboard/`, `/teams/`, `/pips/`.
- Do not open realm links in a new tab. Do not persist the active sidebar item.
- Do not keep an icon-only rail. Collapsed width is 0.
- MCP and agents are out of scope.
- Embed responses stay navbar-free.

## Section C — SAO sections

- Web UI Architecture / UI Design Conventions — FOB shell paragraph. N5 drops the sentence that production templates adopt this in a later BPE.
- Why Not JavaScript Frameworks, Django Implementation Details, Testing Strategy.
- Three-Panel Layout — Content Browser only.

## Section D — Tests to Create

- `test_app_shell_log_story_happy` — authenticated `/playbooks/` logs section `playbooks` and authenticated chrome.
- `test_app_shell_log_story_guest` — anonymous `/` logs guest chrome.
- Update `tests/integration/test_base_shell.py` and `tests/integration/test_navbar_links.py`: `realm-navbar`, `app-sidebar`, realm testids `realm-nav-featurefactory` through `realm-nav-heimdall`, existing `nav-*` testids, guest Register/Login, no search/bell/user menu.
- Update `tests/integration/test_embed_views.py`: full page contains `realm-navbar`; embed contains neither `main-navbar` nor `realm-navbar`.
- `tests/unit/test_primary_nav_section.py`: keep URL-to-section cases; assert realm list and chrome flag.
- `tests/e2e/test_content_browser_detail_panel.py`: popup contains `realm-navbar`.

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `primary_nav_section` | entry | context processor runs | `path=` |
| `primary_nav_section` | branch | anonymous request | `chrome=guest` |
| `primary_nav_section` | branch | authenticated request | `chrome=authenticated` |
| `primary_nav_section` | exit | section resolved | `nav_section=` |

No tokens, passwords, or emails. Prove with `tests/support/log_story.py` `assert_log_story`.

## Section F — MCP Tools to Expose

Not applicable.

## Section H — Mockup Graduation Plan

| Screen | Mockup source | Production target | Strategy | BPE-03 node id |
|--------|---------------|-------------------|----------|----------------|
| Authenticated shell | `templates/mockups/nav/_shell.html` | `templates/base.html` | rewire | N2-graduate-shell |
| Playbooks active state | `templates/mockups/nav/playbooks.html` | `templates/base.html` via `nav_section` | rewire | N2-graduate-shell |
| Guest shell | `templates/mockups/nav/guest.html` | `templates/base.html` anonymous branch | rewire | N2-graduate-shell |
| Mobile offcanvas | `templates/mockups/nav/mobile.html` | `templates/base.html` `offcanvas-lg` | rewire | N2-graduate-shell |
| Collapse | inline style in `_shell.html` | `static/css/mimir-app.css` | rewire | N2-graduate-shell |

Mockup pages keep extending `_shell.html`.

## Feature execution graph

See `docs/plans/FOB_REALM_NAV_SIDEBAR-feature-execution-graph.yaml`.

<!-- FEATURE_EXECUTION_GRAPH -->
feature_execution_graph:
  feature_ref: FOB-REALM-NAV-SIDEBAR
  nodes:
    - id: N1-shell-context
      bpe: BPE-02
      depends_on: []
      gate:
        command: pytest tests/unit/test_primary_nav_section.py tests/integration/test_app_shell_log_story.py -x
        log_story_command: pytest tests/integration/test_app_shell_log_story.py -k log_story -x
    - id: N2-graduate-shell
      bpe: BPE-03
      depends_on: [N1-shell-context]
      gate:
        command: pytest tests/integration/test_base_shell.py tests/integration/test_navbar_links.py tests/integration/test_embed_views.py -x
    - id: N3-acceptance
      bpe: BPE-04
      depends_on: [N2-graduate-shell]
      gate:
        command: pytest tests/integration/test_base_shell.py tests/integration/test_navbar_links.py tests/integration/test_embed_views.py tests/integration/test_guest_playbook_browse.py -x
    - id: N4-e2e-chrome
      bpe: BPE-05
      depends_on: [N3-acceptance]
      gate:
        command: pytest tests/e2e/test_content_browser_detail_panel.py -k navbar -x
    - id: N5-dod
      bpe: BPE-06
      depends_on: [N4-e2e-chrome]
      gate:
        command: pytest tests/integration/test_base_shell.py tests/integration/test_navbar_links.py tests/integration/test_app_shell_log_story.py -x
<!-- /FEATURE_EXECUTION_GRAPH -->

N4 needs Playwright. Do not weaken the `realm-navbar` assertion. If the browser cannot launch, record that on the node and do not delete the assertion.

## Lessons Learned

The reconciliation updated only `guest-navbar.feature` and `navigation.feature`. List, guest-browse, agents, and Content Browser access scenarios still said "main navigation", so a cold implementor can rebuild the old bar. The screen-flow diagram was deferred and is a required BPE-01 input. A template-only N2 would fail the existing shell tests and force a footprint violation, so those assertions travel with `base.html`.

## Checklist

- [x] Spec phrases in living feature files and `docs/plans/UX_WORKFLOW.md` name the app sidebar
- [x] Screen-flow entry note added
- [ ] `build_shell_context` stub, then N1 log story
- [ ] N2 production shell
- [ ] N3 guest browse gate
- [ ] N4 Content Browser popup assertion
- [ ] N5 SAO sentence and reconciliation checklist
