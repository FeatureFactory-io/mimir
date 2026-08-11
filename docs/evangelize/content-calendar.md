# Content Calendar

Episode roster, **persona content catalog**, arc-batch scheduling, and launch template.

See [content-pipeline.md](./content-pipeline.md) for the per-episode spine (teaser → announce → webinar → long video → clips).

**Sources for this catalog**

| Source | What it defines |
|--------|-----------------|
| [`docs/ideation/target_user_classes.md`](../ideation/target_user_classes.md) | JTBD, pains, value props per class |
| [`templates/methodology/use_cases.html`](../../templates/methodology/use_cases.html) | Shipped “In Cursor, say…” prompts (`job-*` cards) |
| [`docs/features/user_journey.md`](../features/user_journey.md) | Acts: guest browse, export/import, PIPs, teams, MCP sync |
| [`.cursor/playbooks/Edda/`](../../.cursor/playbooks/Edda/) | FeatureFactory workflows (ESM, BPE, DCI, DCD, MIN, …) |

---

## Readiness legend

| Mark | Meaning | Evangelize? |
|------|---------|-------------|
| 🟢 | Demo-ready in Mimir today (UI and/or MCP) | Webinar + video |
| 🟡 | Demo-ready with extra prereqs (GitHub milestone, second repo, multi-step) | Webinar with pre-work; or long video only |
| 🔵 | Companion product or narrative (e.g. Huginn) | Cross-promo; label clearly |
| ⚪ | Ideation only — not in product yet | Do not schedule until built |

---

## Content catalog by target class

Each row is one **presentable unit** (webinar, long video, or short). IDs are stable references for arc batches below.

### Lead Engineer

*Value prop:* standards applied consistently; task briefs in minutes; PR feedback anchored in craft.

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **LE-01** | Encode your standards once — playbook, workflow, rules, agents | job-lead-1 · target § Lead #1–2 | `create_playbook` + workflow + activity; optional `set_activity_rules` | Webinar | 🟢 |
| **LE-02** | Export BPE to `.cursor/playbooks` — IDE picks it up every session | job-lead-4 | `export_workflow_to_local` → `.cursor/playbooks/Edda/BPE` | Webinar + teaser | 🟢 |
| **LE-03** | PR review against the playbook, not your opinion | job-lead-3 · target § feedback | Read BPE-02 activity + review diff against rules | Webinar | 🟢 |
| **LE-04** | Read the right activity before you start the task | job-lead-2 | `get_activity` / natural-language read BPE-02 | Short or webinar segment | 🟢 |
| **LE-05** | Turn `.cursor/` / `.windsurf/` into portable **My Craft** playbook | job-lead-5 · Playbook for Playbooks | Import from local rules + workflow structure | Webinar | 🟢 |
| **LE-06** | Evolve standards via PIP — versioned like code | target § Lead #6 · Act 9 | Export → edit locally → `create_pip_from_protocol` on released playbook | Webinar | 🟡 |
| **LE-07** | Fix a bug the BPE-09 way | BPE-09 · quick ideas PR workflow | `@.cursor/playbooks/Edda/BPE/BPE-09-Fix_Bug.md` | Short + optional live Q&A | 🟢 |
| **LE-08** | Generate a task brief from a feature spec | target § task brief · BPE-01 | BPE-01 Plan Feature → implementation plan artifact | Webinar | 🟢 |
| **LE-09** | Export → AI edit → import workflow (draft playbook) | user_journey Act 3.5 · export-import.feature | `export_workflow_to_local` → edit md → `apply_upload_protocol` | Webinar | 🟢 |
| **LE-10** | Attach rules and agents to activities | Act 7–8 · rules CRUDLF | `set_activity_rules`, `link_agent_to_activity` | Short | 🟢 |

### Junior Engineer

*Value prop:* guided steps, checklists, confidence; same playbook the lead uses.

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **JR-01** | Get walked through the task before writing code | job-jr-1 · target § Guide | Read Edda activity step-by-step with whys | Webinar | 🟢 |
| **JR-02** | Verify work against Definition of Done before PR | job-jr-2 · target § Checklist | BPE-06 Check Definition of Done | Webinar | 🟢 |
| **JR-03** | Run feature acceptance tests the BPE-04 way | target § Checklist | BPE-04 Implement Feature Acceptance Tests | Webinar | 🟢 |
| **JR-04** | Fix a bug with the playbook as coach (not judgment) | BPE-09 · Steve agent idea | BPE-09 + explain-as-you-go prompt | Short | 🟢 |
| **JR-05** | Explore a public playbook as a guest — no account yet | user_journey Act 0.5 | Guest browse released public playbook + Content Browser | Short | 🟢 |

### Scrum Master

*Value prop:* consistent issues, dependency confidence, plain-language sprint health.

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **SM-01** | Check sprint readiness before kickoff | job-sm-1 · target § dependency check | "Are we ready for BPE on milestone #N?" + iteration labels | Webinar | 🟡 |
| **SM-02** | Generate milestone issues from BPE — same structure every sprint | job-sm-2 · target § milestone decomposition | Read BPE workflow → create GitHub issues w/ checkpoints | Webinar | 🟡 |
| **SM-03** | See cross-workflow dependencies before planning slips | target § coverage · Content Browser | Content Browser graph for Edda playbook | Short | 🟢 |
| **SM-04** | Run a milestone dark-factory style (MIN workflow) | iteration protocol · dark-factory skill | MIN-03 sequence from manifest + status labels | Webinar | 🟡 |
| **SM-05** | Plain-language sprint health | target § sprint health | 🔵 Pair with Huginn SitRep demo — Mimir supplies BPE playbook context | Cross-promo | 🔵 |

### Competency Center Head

*Value prop:* retain knowledge, release standards, share methodology, showcase expertise.

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **CC-01** | Capture domain methodology as a structured playbook | job-cc-1 · target § knowledge retention | Create playbook + workflow + activities (e.g. data engineering) | Webinar | 🟢 |
| **CC-02** | Release at v1.0 — locked standard; changes via PIP | job-cc-2 | Playbook detail → **[Release]**; MCP read-only on v≥1.0 | Webinar | 🟢 |
| **CC-03** | Hand a workflow to another team (JSON export/import) | job-cc-3 | Workflow → Export JSON → recipient Import | Webinar | 🟢 |
| **CC-04** | Publish a public playbook — guests evaluate before registering | user_journey Act 0.5 | Public + Released visibility; guest browse | Short | 🟢 |
| **CC-05** | Curate released playbooks on a Team | Act 11 teams | Create team → add released playbook → members get access | Webinar | 🟢 |
| **CC-06** | Export full playbook to local AI workspace | export-import.feature · MCP | `export_playbook_to_local` | Webinar | 🟢 |
| **CC-07** | Govern improvements — PIP submit → review → accept | Act 9 PIPs | `create_pip` → submit → preview diff | Webinar | 🟡 |
| **CC-08** | RFP answer draft from playbook in under an hour | target § RFP · gain creators | RFP playbook (ideation) | — | ⚪ |
| **CC-09** | Expertise discovery from inbox | target § expertise by tag | Expertise Discovery playbook (ideation) | — | ⚪ |

### Team Lead / Program Lead

*Maps to Lead Engineer + CC Head jobs; distinct “program” framing for promo.*

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **TL-01** | Share your TDD playbook with every squad on the program | strategy example · job-lead-1 + CC-03 | Encode standards → release → export/import per squad | Webinar | 🟢 |
| **TL-02** | Same AI rules in every IDE — export once, many repos | LE-02 at program scale | `export_workflow_to_local` per team repo + Docker MCP setup | Webinar | 🟡 |
| **TL-03** | Onboard a new squad — point them at the team playbook | target Lead § onboarding | Team playbooks tab + export to their Cursor | Short | 🟢 |

### Product Owner / Product-minded lead

*Not on use_cases.html yet — map to ESM + BPE inception path.*

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **PO-01** | Plan a feature the BPE-01 way | BPE-01 · feature specs | BPE-01 → implementation plan in `docs/plans/` | Webinar | 🟢 |
| **PO-02** | Define user journey + Gherkin before code | ESM-02 · ESM-05 | ESM workflow → `docs/features/` feature files | Webinar | 🟢 |
| **PO-03** | Build a POC using Edda — inception slice in one session | strategy example | ESM-02 + ESM-05 + BPE-01 (no full BPE delivery) | Webinar | 🟡 |
| **PO-04** | From mockup to production screen | ESM-06 → BPE-03 | Mockup graduation table in BPE-01 / BPE-03 | Webinar | 🟡 |
| **PO-05** | Process a change request without scope creep | BPE-08 | BPE-08 Process Change Request | Short | 🟢 |

### Release Engineer / Platform Engineer

*Not on use_cases.html yet — map to DCI/DCD + share pattern from CC Head.*

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **RE-01** | Turn SAO into infra requirements | DCI-01 | DCI-01 Review SAO & Define Infra Requirements | Webinar | 🟢 |
| **RE-02** | Encode compute / storage / networking as playbook workflows | DCI-04 · DCI-05 · DTA-15 | DCI CDK stack activities + infra artifacts | Webinar | 🟡 |
| **RE-03** | Ship CI/CD pipeline guidance as activities | DCD workflow · DTA-10 | DCD-01…DCD-07 + `artifacts/ci-pipeline-github-actions.md` | Webinar | 🟡 |
| **RE-04** | Share infra blueprints with the department | strategy example · CC-03 | Domain playbook + workflow JSON handoff | Webinar | 🟢 |
| **RE-05** | Export infra workflow to platform team repos | LE-02 pattern | `export_workflow_to_local` for DCI or DCD | Short | 🟢 |

### Project Manager

*Most JTBD lives in Huginn; Mimir supplies the **Manage Project** playbook context (planned).*

| ID | Outcome title | JTBD / source | Demo anchor | Format | Ready |
|----|---------------|---------------|-------------|--------|-------|
| **PM-01** | Morning SitRep — one read, anomalies first | target § Daily SitRep | 🔵 Huginn Gjallarhorn demo; mention Edda as process source | Cross-promo | 🔵 |
| **PM-02** | Master Variables — what good looks like for throughput & quality | target § leading indicators | 🔵 Huginn OODA composite narrative | Long video | 🔵 |
| **PM-03** | Trace roadmap milestone → BPE issues → done | target § traceability | SM-02 + iteration `status-done` labels | Webinar | 🟡 |
| **PM-04** | Manage Project playbook in Mimir | target § pain relievers | Manage Project workflow | — | ⚪ |

---

## Catalog summary

| Target class | 🟢 Demo-ready | 🟡 With prereqs | 🔵 / ⚪ Hold |
|--------------|---------------|-----------------|-------------|
| Lead Engineer | 8 | 2 | — |
| Junior Engineer | 5 | — | — |
| Scrum Master | 1 | 3 | 1 (Huginn) |
| Competency Center Head | 6 | 2 | 2 (ideation) |
| Team Lead / Program | 2 | 1 | — |
| Product Owner | 3 | 2 | — |
| Release Engineer | 2 | 2 | — |
| Project Manager | — | 1 | 3 |

**Minimum viable Season 1:** 18 webinars covering all 🟢 items for Lead, Junior, CC, TL, plus one SM and one PO/RE each.

---

## Scheduling model: arc batches

Group **2–3 catalog IDs** into story arcs; do not exhaust one persona (LE has 10 items) or rotate shallowly forever.

```text
Batch 1  encode → use → scale     LE-02 → JR-01 → CC-02 + CC-03
Batch 2  lead craft depth         LE-03 → LE-07
Batch 3  planning & program       SM-01 → SM-02 → TL-01
Batch 4  authoring & import       LE-05 → LE-09 → CC-06
Batch 5  org & community           CC-05 → CC-04 → CC-07
Batch 6  inception & platform     PO-03 → PO-02 → RE-04
Batch 7  governance & scale       LE-06 → TL-02 → RE-05
```

### After Wave 1 — decision rule

| Signal | Next move |
|--------|-----------|
| Registrations skew one persona | **Depth batch** — next 2 IDs from that class's catalog (max 2 in a row) |
| Even spread / cold start | Next **arc batch** in order |
| Episode underperformed | Swap in adjacent catalog ID (same persona or same arc theme) |

Cap **two consecutive episodes** on the same persona unless metrics demand a third.

---

## Season 1 — recommended live sequence

Wave 1 (Ep 1–3): **free**. Wave 2 (Ep 4+): **$5 public** optional; direct invites free. Replay public 7–14 days after live.

| Ep | Catalog | Persona | Outcome title (live) |
|----|---------|---------|----------------------|
| **1** | LE-02 | Lead Engineer | Export BPE to Cursor — every dev and AI gets the same protocol |
| **2** | JR-01 | Junior Engineer | Read BPE-02 before you write a line of code |
| **3** | CC-02 + CC-03 | CC Head | Release at v1.0 + hand workflow JSON to another team |
| **4** | LE-03 | Lead Engineer | PR review against the playbook, not your opinion |
| **5** | LE-07 | Lead Engineer | Bug fixed the BPE-09 way *(short-heavy)* |
| **6** | SM-01 | Scrum Master | Are we ready for BPE on milestone #N? |
| **7** | SM-02 | Scrum Master | Generate sprint issues from BPE — consistent every time |
| **8** | TL-01 | Team Lead | Share your TDD playbook with every squad on the program |
| **9** | LE-05 | Lead Engineer | Turn `.cursor/` into portable **My Craft** playbook |
| **10** | PO-02 | Product Owner | User journey + Gherkin before code (ESM) |
| **11** | PO-01 | Product Owner | Plan a feature the BPE-01 way |
| **12** | RE-04 | Release Engineer | Share infra blueprints with the department |
| **13** | CC-05 | CC Head | Curate released playbooks on a Team |
| **14** | LE-09 | Lead Engineer | Export → AI edit → import workflow (draft playbook) |
| **15** | JR-02 | Junior Engineer | Verify against Definition of Done (BPE-06) |
| **16** | CC-07 | CC Head | Govern playbook changes — PIP submit to accept |
| **17** | PO-03 | Product Owner | Build a POC using Edda — inception in one session |
| **18** | RE-01 | Release Engineer | Turn SAO into infra requirements (DCI-01) |

**Season 1 shorts backlog** (native teasers between live events): LE-02 teaser, JR-05, SM-03, CC-04, LE-07, LE-10, PO-05, RE-05, TL-03.

**Season 2 candidates:** LE-01, LE-06, LE-08, JR-03, JR-04, SM-04, CC-01, CC-06, PO-04, RE-02, RE-03, PM-03; cross-promo PM-01/PM-02 with Huginn.

---

## 12-week launch sequence (Ep 1–7 + buffer)

First production season starts with Batch 1–3. Overlap clip posting with next teaser — see [content-pipeline.md](./content-pipeline.md).

| Week | Batch | Live (catalog ID) | Publish long | Shorts / social |
|------|-------|-------------------|--------------|-----------------|
| 1 | B1 | — | — | Teaser **LE-02**; announce Ep 1 |
| 2 | B1 | **Ep 1** LE-02 | — | Thank-you; clips from teaser |
| 3 | B1 | **Ep 2** JR-01 | Ep 1 long | 3 clips Ep 1; teaser JR-01 |
| 4 | B1 | **Ep 3** CC-02/03 | Ep 2 long | 3 clips Ep 2; teaser CC |
| 5 | — | — | Ep 3 long | 3 clips Ep 3; **CC-04** short |
| 6 | B2 | **Ep 4** LE-03 ($5 OK) | — | Teaser LE-03 |
| 7 | B2 | **Ep 5** LE-07 | Ep 4 long | 3 clips Ep 4; native LE-07 |
| 8 | B3 | **Ep 6** SM-01 ($5) | Ep 5 long | 3 clips Ep 5; **SM-03** short |
| 9 | B3 | **Ep 7** SM-02 ($5) | Ep 6 long | 3 clips Ep 6 |
| 10 | B3 | **Ep 8** TL-01 ($5) | Ep 7 long | 3 clips Ep 7; retrospective |
| 11–12 | B4+ | Ep 9+ or shorts-only | Ep 8 long | 2 native shorts/week; plan Season 1 Ep 9–18 |

---

## Gaps before promoting a catalog item

| Catalog IDs | Gap |
|-------------|-----|
| PO-01 … PO-04 | Add **Product Owner** section to `use_cases.html` |
| RE-01 … RE-05 | Add **Release Engineer** section to `use_cases.html` |
| SM-01, SM-02, SM-04, PM-03 | Pre-work doc: GitHub milestone + labels; sample milestone in demo repo |
| TL-02 | Docker MCP bind-mount doc prominent in pre-work |
| CC-07, LE-06 | Released playbook + sample PIP in seed data for demo |
| PM-01, PM-02 | Huginn demo environment or recorded segment |
| CC-08, CC-09, PM-04 | Product not built — do not schedule |

### Launch infrastructure

- [ ] Event landing / Eventbrite $5 SKU (before Batch 2 $5 events)
- [ ] YouTube *FeatureFactory — building in the open*
- [ ] Post-event survey (MCP connected Y/N)
- [ ] Newsletter / mailing list

---

## Episode brief template

```markdown
## Ep N — [Outcome title]

**Catalog ID:** e.g. LE-02
**Arc / batch:** B1 | B2 | …
**Persona:** [role]
**Readiness:** 🟢 | 🟡 | 🔵
**Date:** YYYY-MM-DD HH:MM TZ
**Pricing:** free | $5 | invite-only
**Use-case / journey anchor:** job-* or Act *
**Prior episode hook:** [catalog ID to reference]

### Promise
In 30 minutes you will: [single sentence outcome]

### Pre-work
- [ ] Register + token
- [ ] Cursor + MCP ([DOCKER_QUICK_START](../DOCKER_QUICK_START.md))
- [ ] [GitHub milestone #N / clone / …]

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
```
