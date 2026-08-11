# Webinar Format

Standard run-of-show for 30-minute Mimir code-alongs.

## Event specs

| Field | Value |
|-------|-------|
| Duration | 30 min live (+ optional 15 min office hours) |
| Platform | Zoom / Google Meet / StreamYard (screen share + chat) |
| Host setup | Cursor + Mimir MCP connected; second monitor for chat |
| Attendee prereq | Completed [pre-work](#pre-work-email) |

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
