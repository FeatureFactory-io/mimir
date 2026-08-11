# Content Calendar

Episode roster, **arc-batch scheduling**, and 12-week launch template. Adjust dates when scheduling; keep persona → outcome → use-case mapping stable.

See [content-pipeline.md](./content-pipeline.md) for the per-episode spine (teaser → announce → webinar → long video → clips).

---

## Scheduling model: arc batches

**Do not** exhaust one persona (Lead Engineer has five jobs — five weeks of “for leads only” starves discovery).

**Do not** strict round-robin forever (one shallow touch per persona, repeat — no depth or narrative).

**Do:** group episodes into **arc batches of 2–3** that follow how methodology flows through a team, then rotate.

```text
Batch 1 (encode → use → scale)     Batch 2 (lead depth)        Batch 3 (planning & program)
  Lead → Junior → CC Head      →     Lead × 2              →     SM → Team Lead / CC Head
```

### After Wave 1 — decision rule

| Signal | Next move |
|--------|-----------|
| Registrations skew one persona | **Depth batch** for that role (max 2 episodes, then rotate) |
| Even spread / cold start | **Arc batch** (2–3 episodes, cross-role story) |
| One episode underperformed | Rotate to a different persona — do not exhaust the flop |

### Depth limit

Cap **two consecutive episodes** on the same persona unless metrics strongly favor a third. Lead Engineer has five use-case jobs — spread them across batches, not one block.

---

## Batch 1 — Methodology flows through the team (Wave 1, free)

**Story:** Someone encodes standards → juniors consume them → org releases and shares.

| Ep | Persona | Outcome title | Use-case anchor | Key MCP / UI moment |
|----|---------|---------------|-----------------|---------------------|
| **1** | Lead Engineer | Export BPE to Cursor — every dev and AI gets the same protocol | `#lead-engineer` · job-lead-4 | `export_workflow_to_local` → `.cursor/playbooks/Edda/BPE` |
| **2** | Junior Engineer | Read BPE-02 before you write a line of code | `#junior-engineer` · job-jr-1 | Read activity + step-by-step guidance |
| **3** | Competency Center Head | Release at v1.0 + hand the workflow to another team | `#cc-head` · job-cc-2, job-cc-3 | Release in UI + Export JSON / Import |

**Teaser copy thread:** Ep 2 teaser references Ep 1 (“You saw export last week — this is what juniors do with it”). Ep 3 teaser references Ep 1–2 (“Now scale it to the org”).

**Pre-launch:** Short teaser for Ep 1 (native) before any webinar — see [content-pipeline.md](./content-pipeline.md).

---

## Batch 2 — Lead craft depth (Wave 2 starts; $5 public fee optional)

**Story:** Same lead audience, deeper jobs — only after Batch 1 established what a playbook is.

| Ep | Persona | Outcome title | Use-case anchor | Notes |
|----|---------|---------------|-----------------|-------|
| **4** | Lead Engineer | PR review against the playbook, not your opinion | `#lead-engineer` · job-lead-3 | Full webinar |
| **5** | Lead Engineer | Bug fixed the BPE-09 way | `BPE/BPE-09-Fix_Bug.md` | Short-heavy; optional 20-min live Q&A |

---

## Batch 3 — Planning & program (Wave 2 continued)

**Story:** Sprint planning and cross-squad sharing — lands better once viewers know playbooks from Batch 1.

| Ep | Persona | Outcome title | Use-case anchor | Notes |
|----|---------|---------------|-----------------|-------|
| **6** | Scrum Master | Sprint readiness + generate milestone issues | `#scrum-master` · job-sm-1, job-sm-2 | Needs GitHub milestone context |
| **7** | Team Lead / CC Head | Share your TDD playbook with every squad on the program | job-lead-1 + job-cc-3 | Program-scale narrative |

---

## Batch 4 — Expansion personas (after landing-page gaps closed)

| Ep | Persona | Outcome title | Prerequisite |
|----|---------|---------------|--------------|
| **8** | Lead Engineer | Turn `.cursor/` rules into portable "My Craft" playbook | job-lead-5 |
| **9** | Product Owner | Build a POC using Edda in one session | **Add PO section to use_cases** |
| **10** | Release Engineer | Package infra blueprints as a department playbook | **Add RE section to use_cases** |

Defer PM / Huginn SitRep until Manage Project workflow story is ready (`target_user_classes.md`).

---

## Short-clip backlog

Record standalone (teasers) or cut from webinars (clips).

| Clip title | Activity / path | Persona | Best batch |
|------------|-----------------|---------|------------|
| One command: BPE in `.cursor/playbooks` | job-lead-4 | Lead Engineer | Pre–Ep 1 teaser |
| Bug fixed the BPE-09 way | `BPE/BPE-09-Fix_Bug.md` | Lead Engineer | Batch 2 / Ep 5 |
| PR review against the playbook | job-lead-3 | Lead Engineer | Batch 2 / Ep 4 |
| Definition of Done checklist | job-jr-2 · BPE-06 | Junior Engineer | Batch 1 / Ep 2 |
| Released playbook = PIP for changes | job-cc-2 | CC Head | Batch 1 / Ep 3 |
| Workflows available to other projects | job-cc-3 | CC Head | Batch 3 / Ep 7 |

---

## 12-week launch sequence

Aligned to arc batches + [content-pipeline](./content-pipeline.md) spine. Overlap clip posting with the next episode's teaser — no dead weeks.

| Week | Arc | Live webinar | Publish long | Shorts / social |
|------|-----|--------------|--------------|-----------------|
| 1 | B1 | — | — | **Teaser** Ep 1; announce Ep 1 |
| 2 | B1 | **Ep 1** Lead — export BPE | — | Clips from teaser; thank-you email |
| 3 | B1 | **Ep 2** Junior — BPE-02 | Ep 1 long public | 3 clips Ep 1; teaser Ep 2 |
| 4 | B1 | **Ep 3** CC Head — release + share | Ep 2 long | 3 clips Ep 2; teaser Ep 3 |
| 5 | — | — (buffer / edit) | Ep 3 long | 3 clips Ep 3 |
| 6 | B2 | **Ep 4** Lead — PR review ($5 OK) | — | Teaser Ep 4; SM communities lurk |
| 7 | B2 | **Ep 5** Lead — BPE-09 (short-heavy) | Ep 4 long | 3 clips Ep 4; native BPE-09 short |
| 8 | B3 | **Ep 6** Scrum Master ($5) | Ep 5 long | 3 clips Ep 5; teaser Ep 6 |
| 9 | B3 | **Ep 7** Team Lead — program share ($5) | Ep 6 long | 3 clips Ep 6; teaser Ep 7 |
| 10 | — | — | Ep 7 long | 3 clips Ep 7; retrospective post |
| 11 | B4 | **Ep 8** My Craft playbook (optional) | — | Review metrics; pick Batch 4 ep |
| 12 | — | Plan next season | Ep 8 long if ran | 2 native shorts/week; waitlist |

---

## Episode brief template

Copy for each new webinar:

```markdown
## Ep N — [Outcome title]

**Arc / batch:** B1 | B2 | B3 | B4
**Persona:** [role]
**Date:** YYYY-MM-DD HH:MM TZ
**Pricing:** free | $5 | invite-only
**Use-case card:** [link to anchor + data-testid]
**Prior episode hook:** [what to reference from last ep, if any]

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
- [ ] Teaser (pre-live): ...
- [ ] Clip 1: ...
- [ ] Clip 2: ...

### Links (UTM)
- Register: ...&utm_medium=announce
- Teaser: ...&utm_medium=teaser
- Replay: ...&utm_medium=video
- Use cases: ...
```

---

## Gaps before Batch 3–4 promotion

- [ ] Add **Product Owner** section to `use_cases.html` (before Ep 9)
- [ ] Add **Release Engineer** section to `use_cases.html` (before Ep 10)
- [ ] Event landing page or Simple Eventbrite with $5 SKU (before Batch 2 $5 events)
- [ ] YouTube channel *FeatureFactory — building in the open* created
- [ ] Post-event survey (MCP connected Y/N)
- [ ] Newsletter / mailing list endpoint for replay + next event
