# Implementation Plan: Landing Hero Primary CTA (BPE-01)

**Feature**: FOB-LANDING-CTA — Register vs Connect MCP hero button  
**Spec**: [`docs/features/act-0-auth/landing-hero-cta.feature`](../features/act-0-auth/landing-hero-cta.feature)  
**Type**: Template-only change request (no backend/MCP)

---

## Section A — Context Map

| File | Lines | Note |
|------|-------|------|
| [`templates/methodology/index.html`](../templates/methodology/index.html) | 22–27 | Hero CTA row — conditional Register vs Connect MCP |
| [`templates/base.html`](../../templates/base.html) | 259–264 | Navbar Register icon reference (`fa-user-plus`) |
| [`templates/methodology/index.html`](../templates/methodology/index.html) | 34–37 | MCP section header plug icon reference |
| [`methodology/views.py`](../methodology/views.py) | 16–23 | `index` view — public landing, no change required |
| [`tests/integration/test_landing_hero_cta.py`](../../tests/integration/test_landing_hero_cta.py) | — | New integration tests (RED → GREEN) |

---

## Section B — Do-Not-Do List

- Do not add Django Forms or new views
- Do not change MCP configuration content or token flow
- Do not duplicate Connect MCP as both text link and button on the same hero row
- Do not change navbar Register/Login markup (reference only)

---

## Section C — SAO.md Sections That Apply

- § Frontend: Django templates, manual rendering, `data-testid` on interactive elements
- § Public access: `/` landing allows anonymous and authenticated sessions

---

## Section D — Tests to Create

| Test | Asserts |
|------|---------|
| `test_guest_landing_shows_register_with_user_plus_icon` | `landing-cta-register` present; `fa-user-plus` in hero; `landing-cta-connect-mcp` absent |
| `test_authenticated_landing_shows_connect_mcp_primary_button` | `landing-cta-connect-mcp` present; `btn-primary`; `fa-plug`; `landing-cta-register` absent |
| `test_connect_mcp_button_links_to_mcp_section` | href contains `#mcp-config`; `landing-mcp-connect` id exists on page |

Log story: **Not applicable** — static template branch only; no new server-side decision points.

---

## Section E — Log Story Script

Not applicable (template conditional only; no new service/view logging required).

---

## Section F — MCP Tools to Expose

Not applicable.

---

## Implementation Steps

1. Add feature spec `landing-hero-cta.feature` (done)
2. RED: `tests/integration/test_landing_hero_cta.py`
3. GREEN: Update hero CTA block in `templates/methodology/index.html`
4. Run targeted pytest; commit in slices

---

## UI Target

**Guest hero row:** `What Mimir Can Do` | `Explore public playbooks` | **`Register`** (btn-success lg, `fa-user-plus`)

**Authenticated hero row:** `What Mimir Can Do` | `Explore public playbooks` | **`Connect MCP`** (btn-primary lg, `fa-plug`, href `#mcp-config`)

Remove standalone `landing-cta-connect` text link from hero (replaced by authenticated primary button).

---

## Commit Strategy

1. `docs(features): landing hero CTA scenarios`
2. `test(landing): hero Register vs Connect MCP CTAs`
3. `feat(ui): conditional landing hero primary action with icons`
