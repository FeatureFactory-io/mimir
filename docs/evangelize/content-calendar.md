# Content Calendar

Pilot roster and 12-week launch sequence. Adjust dates when scheduling; keep persona → outcome → use-case mapping stable.

## Pilot roster (Wave 1 — free or PWYW)

Each episode maps to a section on **What Mimir Can Do** and a `job-*` card in `use_cases.html`.

| # | Persona | Outcome title | Use-case anchor | Key MCP / UI moment |
|---|---------|---------------|-----------------|---------------------|
| 1 | Lead Engineer | Encode standards once; export BPE to Cursor | `#lead-engineer` · job-lead-4 | `export_workflow_to_local` → `.cursor/playbooks/Edda/BPE` |
| 2 | Scrum Master | Sprint readiness + generate milestone issues | `#scrum-master` · job-sm-1, job-sm-2 | "Are we ready for BPE on milestone #N?" |
| 3 | Competency Center Head | Release v1.0 + share workflow across teams | `#cc-head` · job-cc-2, job-cc-3 | Release in UI + Export JSON / Import |
| 4 | Junior Engineer | Walk through BPE-02 before writing code | `#junior-engineer` · job-jr-1 | Read activity + step-by-step guidance |

## Wave 2 episodes (introduce $5 public fee)

| # | Persona | Outcome title | Notes |
|---|---------|---------------|-------|
| 5 | Team Lead | Share TDD playbook with every squad on the program | Extend job-lead-1 + team/export narrative |
| 6 | Product Owner | Build a POC using Edda in one session | **Add PO section to use_cases first** |
| 7 | Release Engineer | Package infra blueprints as a department playbook | **Add RE section to use_cases first** |
| 8 | Lead Engineer | Turn `.cursor/` rules into portable "My Craft" playbook | job-lead-5 · Playbook for Playbooks |

## Short-clip backlog (record standalone or cut from pilots)

| Clip title | Activity / path | Persona |
|------------|-----------------|---------|
| Bug fixed the BPE-09 way | `BPE/BPE-09-Fix_Bug.md` | Lead Engineer |
| PR review against the playbook | job-lead-3 | Lead Engineer |
| Definition of Done checklist | job-jr-2 · BPE-06 | Junior Engineer |
| Released playbook = PIP for changes | job-cc-2 | CC Head |
| Make workflows available to other projects | job-cc-3 + export/import | CC Head / Release Engineer |

## 12-week launch sequence (template)

| Week | Live | Publish long | Short clips | LinkedIn / community |
|------|------|--------------|-------------|----------------------|
| 1 | Ep 1 live | — | — | Announce Ep 1 |
| 2 | Ep 2 live | Ep 1 long (public) | 3 clips from Ep 1 | Post clip 1–2 |
| 3 | Ep 3 live | Ep 2 long | 3 clips from Ep 2 | Community: Lead Engineer angle |
| 4 | Ep 4 live | Ep 3 long | 3 clips from Ep 3 | Post clip + carousel |
| 5 | — (buffer) | Ep 4 long | 3 clips from Ep 4 | Steady state begins |
| 6 | Ep 5 live ($5) | — | 1 native short (BPE-09) | SM community |
| 7 | Ep 6 live ($5) | Ep 5 long | 3 clips from Ep 5 | |
| 8 | Ep 7 live ($5) | Ep 6 long | 3 clips from Ep 6 | DevOps community |
| 9 | Ep 8 live ($5) | Ep 7 long | 3 clips from Ep 7 | |
| 10 | — | Ep 8 long | 3 clips from Ep 8 | Retrospective post |
| 11–12 | Repeat best performer / new short-only | Back catalog SEO | 2 native shorts/week | Build waitlist for next season |

## Episode brief template

Copy for each new webinar:

```markdown
## Ep N — [Outcome title]

**Persona:** [role]
**Date:** YYYY-MM-DD HH:MM TZ
**Pricing:** free | $5 | invite-only
**Use-case card:** [link to anchor + data-testid]

### Promise
In 30 minutes you will: [single sentence outcome]

### Pre-work
- [ ] Register + token
- [ ] Cursor + MCP (DOCKER_QUICK_START)
- [ ] [Any repo clone]

### Commands (in order)
1. "..."
2. "..."

### Short clips to cut
- [ ] Hook: ...
- [ ] Demo: ...
- [ ] CTA: ...

### Links (UTM)
- Register: ...
- Replay: ...
- Use cases: ...
```

## Gaps before Wave 2 promotion

- [ ] Add **Product Owner** section to `use_cases.html`
- [ ] Add **Release Engineer** section to `use_cases.html`
- [ ] Event landing page or Simple Eventbrite with $5 SKU
- [ ] YouTube channel *FeatureFactory — building in the open* created
- [ ] Post-event survey (MCP connected Y/N)
- [ ] Newsletter / mailing list endpoint for replay + next event
