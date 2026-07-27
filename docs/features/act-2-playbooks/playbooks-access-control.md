# Playbook access control (FOB — target model)

This document is the source of truth for playbook permissions in Mimir FOB.
Feature files under `act-2-playbooks/` and `act-9-pips/` align with this model.

> **MVP note:** The simplified implementation for MVP supports two visibility values:
> **Private** and **Public**. Family, Local, and Homebase sync are deferred.
> Owner PIP finalisation runs through Django Admin for MVP; the in-FOB owner
> finalize UI is the first post-MVP piece.

---

## Visibility

| Value | Who can view | Who can edit (draft) | Who can finalize PIP (released) |
|-------|-------------|----------------------|---------------------------------|
| **Private** | Owner only | Owner only | Owner or Staff admin |
| **Public** | Owner always; **anonymous guests** when `status=released`; **authenticated users** when status ≠ draft | Owner only | Owner or Staff admin |

**Guest vs authenticated asymmetry:** Anonymous users see only **released** public playbooks. Logged-in users also see public playbooks in `active` or `disabled` status (any non-draft).

- Default on creation: **Private**.
- **Draft + Public** is owner-only until the playbook is released (or otherwise leaves draft status).
- Changing from Public → Private immediately hides the playbook from non-owners (and guests).
- Changing from Private → Public immediately makes a **released** playbook readable to anonymous guests; non-draft public playbooks become readable to all logged-in users.

---

## Access by surface

| Surface | Private playbook | Public released (anonymous guest) | Public non-draft (authenticated) | Public draft |
|---------|-----------------|-----------------------------------|----------------------------------|--------------|
| **FOB GUI list `/playbooks/`** | Owner only | Released public playbooks only; guest banner; no Create | Owned + public non-draft cards | Owner only |
| **FOB GUI detail + child VIEW** | Owner only | Read-only; no Edit/Delete/Create/Release/PIP | Read-only for non-owners | Owner only |
| **Global lists** (`/workflows/`, `/activities/`, …) | Login required | Rows from released public playbooks only; no Create | Full accessible set per user | Login required |
| **Playbook-scoped READ lists** (`/playbooks/<pk>/workflows/`, `/playbooks/<pk>/activities/`, workflow activities, artifacts, agents, skills, rules, phases) | Owner only | Allowed when parent playbook is released + public; read-only; no Create | Allowed when public non-draft | Owner only |
| **Content Browser** `/browser/<pk>/` | Owner only | Allowed when released + public | Allowed when public non-draft | Owner only |
| **Graph API** `GET /api/playbooks/<pk>/graph/` | Owner / group | AllowAny + `can_view` when released + public | Same as authenticated public viewer | Owner only |
| **MCP tools** | Owner only (`author=user`) | **Not available** (token required) | Owner only (MCP author-scoped) | Owner only |
| **REST API writes** | Owner or group member | Login required | Owner or group member | Owner only |
| **PIPs** | Owner | Login required | Owner submit; public viewer read-only where applicable | Owner only |

404 (not 403) for inaccessible playbooks — no existence leak for guests.

---

## Lifecycle (status)

- **draft** — editable by owner; version 0.x; auto-increments on save.
- **released** — read-only direct edits; version 1.0+; changes via PIP; **only status visible to anonymous guests** on public playbooks.
- **active** / **disabled** — legacy statuses retained in model; visible to authenticated public viewers when not draft, **not** to anonymous guests.

---

## PIP acceptance (released playbooks)

| Actor | Can submit PIP | Can finalize (accept/reject changes) | Can view playbook content |
|-------|---------------|--------------------------------------|---------------------------|
| **Playbook owner** | Yes | Yes | Yes |
| **Staff admin** (`is_staff`) | No | Yes (Django Admin; in-FOB UI post-MVP) | Yes |
| **Authenticated public viewer** (not owner) | No | No | Yes (read-only) |
| **Anonymous guest** | No | No | Yes (released public playbooks only; no PIP routes) |

> **MVP note:** In-FOB owner finalize UI is not yet built. For MVP, owners
> submit PIPs and staff finalize via Django Admin. The `@mvp_gap` tag marks
> scenarios that describe the owner-finalize FOB UI.

---

## Deferred (not in MVP)

- **Family** visibility (Homebase family sharing)
- **Local only** visibility (exclude from Homebase sync)
- MCP public read access (MCP remains author-scoped; token required)
- REST API group sharing UI in FOB browser
- Anonymous PIP list or submission
- Anonymous global search
- Anonymous `/teams/` browse

---

## Related specs

- `playbooks-guest-browse.feature` — anonymous guest evaluation journey
- `guest-global-entity-lists.feature` — anonymous global entity list routes
- `playbooks-create.feature` — wizard visibility Private / Public, Step 3 draft/released
- `playbooks-edit.feature` — visibility toggle, owner-only write
- `playbooks-list-find.feature` — unified Playbooks card grid; guest and authenticated variants
- `playbooks-view.feature` — public read by authenticated users and anonymous guests
- `playbooks-delete.feature` — public visibility deletion impact
- `pips-admin-review.feature` — owner and admin finalize, public viewer cannot
- `pips-view.feature` — PIP detail visibility for public viewers (login required for guests)
- `docs/features/user_journey.md` — Act 0.5 guest evaluation + Act 2 narrative
