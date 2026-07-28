# Implementation Plan: Guest Full Navbar (BPE-08 Change Request)

**Feature**: FOB-GUEST-NAV — Full primary navbar for anonymous users  
**Spec**: [`docs/features/act-0-auth/guest-navbar.feature`](../features/act-0-auth/guest-navbar.feature)  
**Type**: Template-only change request (no model/service/view work)

---

## Problem Statement

Anonymous users saw a **partial** navbar (Playbooks → Rules) only on browse routes, and **no** entity nav links on the landing page. For system demos and discovery, guests should see the same primary nav as authenticated users (Home → PIPs), with Register/Login on the right instead of search, notifications, and user menu.

Auth-only destinations (Home `/dashboard/`, Teams, PIPs) continue to redirect to login via existing `@login_required` decorators.

---

## Section A — Context Map

| File | Change |
|------|--------|
| [`templates/base.html`](../templates/base.html) | Merge duplicate nav blocks; single primary `<ul>` for all users |
| [`methodology/context_processors.py`](../methodology/context_processors.py) | Remove `guest_browse_nav()` |
| [`mimir/settings/base.py`](../mimir/settings/base.py) | Remove context processor registration |
| [`docs/features/act-0-auth/guest-navbar.feature`](../features/act-0-auth/guest-navbar.feature) | New GUEST-NAV-01..05 scenarios |
| [`docs/ux/IA_guidelines.md`](../ux/IA_guidelines.md) §4.1 | Update anonymous/guest chrome |
| [`docs/features/user_journey.md`](../features/user_journey.md) | Update guest landing + browse |
| Related feature files | AGENT-GLOBAL-13, CB-01c, playbooks-guest-browse GUEST-02 |

---

## Section B — Do-Not-Do List

- Do not grant guest read access to Dashboard, Teams, or PIPs
- Do not expose global search to guests
- Do not change embed templates (`?embed=1`)
- Do not add backend routes or services

---

## Section C — Test Plan

| Test file | Coverage |
|-----------|----------|
| `tests/integration/test_navbar_links.py` | Full nav on `/`; Teams/PIPs redirect |
| `tests/integration/test_guest_playbook_browse.py` | `TestGuestNavbar` full nav + auth widget hiding |
| `tests/integration/test_base_shell.py` | Landing shows all nav testids |
| `tests/unit/test_primary_nav_section.py` | Remove obsolete `guest_browse_nav` tests |

Run:

```bash
.venv/bin/python -m pytest tests/integration/test_guest_playbook_browse.py::TestGuestNavbar \
  tests/integration/test_navbar_links.py tests/unit/test_primary_nav_section.py \
  tests/integration/test_base_shell.py -v
```

---

## Section D — Implementation Steps

1. Update feature specs and IA (source of truth)
2. RED: integration tests for full nav + redirects
3. GREEN: merge `base.html` nav into single block
4. Remove `guest_browse_nav` context processor
5. Verify tests green

---

## Success Criteria

- Anonymous users see Home → PIPs on every `base.html` page
- Register + Login visible; search/bell/user menu hidden
- Authenticated navbar unchanged
- All targeted tests pass
