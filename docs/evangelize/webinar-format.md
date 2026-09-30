# Webinar Format

Standard run-of-show for 30-minute Mimir code-alongs.

## Event specs

| Field | Value |
|-------|-------|
| Duration | 30 min live (+ optional 15 min office hours) |
| Stack | [Luma + Zoom Meeting](#webinar-stack-luma--zoom) (registration, $5 gate, live room, recording) |
| Host setup | Cursor + Mimir MCP connected; second monitor for chat |
| Attendee prereq | Completed [pre-work](#pre-work-email) |

---

## Webinar stack (Luma + Zoom)

**Default engine:** [Luma](https://luma.com) for the event page, payments, and access control; **Zoom Meeting** for the live code-along and cloud recording.

Do **not** use GoToWebinar for this motion (payment still external, poor fit for dev-community code-alongs). Do **not** rely on Zoom alone for a paid gate — checkout and join-link delivery belong on Luma (or Eventbrite).

### Roles

| Layer | Tool | Responsibility |
|-------|------|----------------|
| Event page + gate | **Luma** | Title, description, calendar, Stripe checkout, confirmation email, reminders |
| Live room | **Zoom Meeting** | Host screen share, chat, waiting room, **cloud recording** → YouTube pipeline |
| Product CTA | **Mimir FOB** | Register, MCP token — linked from Luma description and post-event email |

Luma integrates with Zoom: connect at [luma.com/settings](https://luma.com/settings); Luma creates the meeting and only sends the join link to registered guests ([Zoom integration help](https://help.luma.com/p/zoom-integration)).

### Ticket types (every event)

| Ticket | Price | Use |
|--------|-------|-----|
| **General** | $5 (Wave 2+) or $0 / PWYW (Wave 1) | Public LinkedIn / community signups |
| **Complimentary** | $0 | Direct invites; optional **require approval** or private registration link |

Wave 1: free or pay-what-you-want on the same stack — no platform change when introducing $5.

### Zoom Meeting vs Webinar

| | **Meeting** (default) | **Webinar** |
|---|------------------------|-------------|
| Audience | Tens to low hundreds | 100+ broadcast-style |
| Code-along | Host shares screen; paste commands in chat | Same; stricter attendee controls |
| Plan | Usually included on Zoom Pro | Webinar add-on / higher tier |

Start with **Meeting** until attendance or moderation needs justify Webinar.

### Zoom settings (host)

- Waiting room **on**
- Mute participants on entry **on** (host shares screen; attendees follow in Cursor locally)
- Cloud recording **on** (raw file for [content pipeline](./content-pipeline.md))
- Only host can screen share (avoid attendee takeover)
- Optional: require sign-in to Zoom for extra leak resistance (in addition to Luma gate)

### Day-one setup checklist

- [ ] Luma calendar created (e.g. **FeatureFactory — building in the open**)
- [ ] Stripe connected on Luma for paid tickets
- [ ] Zoom account linked in Luma settings
- [ ] Per event: catalog ID + persona in title; link to use-cases anchor + `DOCKER_QUICK_START` in description
- [ ] UTM on shared Luma URL: `?utm_source=linkedin&utm_medium=announce&utm_campaign=<catalog-id>`
- [ ] Test purchase: $5 flow → confirmation email → join link works
- [ ] Test comp ticket: $0 flow for invite list

### Fees at ~$5 (plan accordingly)

Tickets are primarily a **commitment filter**, not revenue.

| Provider | Rough economics on $5 ticket |
|----------|------------------------------|
| **Luma** (free plan) | ~5% platform + Stripe ~2.9% + $0.30 — viable micro-ticket |
| **Eventbrite + Zoom** | Flat **~$1.79**/ticket service fee + processing — buyer often sees **~$7+** unless you raise price or absorb fees |

If checkout feels punitive at $5, absorb fees as marketing cost or price Wave 2 at **$9–12** without changing stack.

### Alternatives (when to switch)

| Stack | When |
|-------|------|
| **Eventbrite + Zoom** | Need Eventbrite discovery; ticket price **$15+** so flat fees hurt less |
| **Luma only (no Zoom)** | Google Meet link pasted manually — OK for pilot; weaker recording workflow |
| **Crowdcast** | All-in-one monetized webinars — less community distribution than Luma |

### Post-registration email flow

1. **Luma automatic:** confirmation + calendar invite + Zoom link (do not post join URL publicly).
2. **Host manual (48h / 24h):** [pre-work email](#pre-work-email) — Mimir register, Cursor, MCP.
3. **Host manual (≤24h after live):** thank-you + unlisted replay + MCP survey + next Luma event link.

---

## Pre-work email (send 48h and 24h before)

Subject: **Before tomorrow: 5 min setup for [Webinar title]**

Checklist for attendees:

1. [Register on Mimir](https://mimir.example/register) and save API token *(use production URL)*
2. Install [Cursor](https://cursor.com)
3. Connect Mimir MCP — follow [`docs/DOCKER_QUICK_START.md`](../DOCKER_QUICK_START.md)
4. *(Optional)* Clone a sandbox repo if the session requires one
5. Join 5 min early for AV check

> **Do not** use live webinar time for first-time MCP install unless labeled "Setup clinic."

## Live run-of-show (30 min)

| Time | Segment | Host actions |
|------|---------|--------------|
| 0:00–2:00 | **Hook** | State persona pain + promised outcome ("In 30 min you'll have X in your IDE") |
| 2:00–5:00 | **Context** | 60 sec on Mimir vs Edda vs FeatureFactory; show use-cases page card you'll complete |
| 5:00–22:00 | **Code-along** | One path only; narrate each MCP prompt; paste commands in chat |
| 22:00–27:00 | **Verify** | Everyone sees same result; troubleshoot top 1–2 failures from chat |
| 27:00–30:00 | **CTA + next** | Register (if guest), connect MCP checklist, link to replay date, next webinar |

## Code-along rules

1. **One outcome** — e.g. export BPE to `.cursor/playbooks/Edda/BPE`, not "full playbook authoring."
2. **Copy from use-cases page** — use exact prompts from `use_cases.html` when possible.
3. **Show MCP tool names** when relevant (`export_workflow_to_local`, `list_activities`, etc.).
4. **No branching** — "If you're on Windows, do this after the session" goes to FAQ doc, not live.
5. **Record everything** — raw recording feeds [content pipeline](./content-pipeline.md).

## Optional office hours (+15 min)

- MCP connection failures
- Docker bind-mount / `MIMIR_DEV_ROOT` issues
- "How would I adapt this to my team?"

## Post-event (within 24h)

1. Email replay link (YouTube unlisted until public release window)
2. Link to relevant **What Mimir Can Do** anchor (e.g. `#lead-engineer`)
3. Survey: "Did you connect MCP?" (single question)
4. Invite to next webinar

## Success criteria

| Level | Criteria |
|-------|----------|
| Minimum | Recording published; 0 critical demo failures |
| Good | ≥50% attendees stay through code-along; chat shows copied commands |
| Great | ≥30% post-survey "MCP connected"; 1+ community question reused as short clip |

## Host preparation checklist

- [ ] Outcome maps to one `data-testid="job-*"` card on use-cases page
- [ ] Dry-run on clean machine (or fresh Docker) in ≤25 min
- [ ] Pre-work email scheduled
- [ ] Chat snippets prepared (commands, links)
- [ ] Fallback: pre-recorded 2-min segment if live MCP fails
- [ ] Event page lists persona + outcome, not generic "Mimir intro"
