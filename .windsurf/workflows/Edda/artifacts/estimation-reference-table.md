# FORGE Estimation Reference Table
**Version:** 3.0 (FP/AFP pricing model added)
**Last updated:** 2026-04-08
**Status:** SEED → PARTIALLY CALIBRATED (1 project, 8 acts measured)

---

## 1. SEED K-Token Baselines

K-token cost per story point, by size tier. Derived for **Django + HTMX + SQLite** stack with **AI-assisted single-dev** workflow (PAF ≈ 1.4×). Adjust for other stacks via TCF.

**Two units — keep them separate:**
- **SP (Story Points)** — internal effort sizing. Used for token budget and duration estimates. Never shown to client.
- **FP (Function Points)** — client-facing deliverable units. Used in the AFP pricing formula. Goes on the quote.

| Size | SP (internal) | FP weight (client) | K min | K expected | K max | Reference story |
|------|:-------------:|:------------------:|------:|-----------:|------:|-----------------|
| XS   | 0.5           | 0.5                |    12 |         22 |    36 | Single HTMX fragment or read-only view |
| S    | 1             | 1                  |    25 |         45 |    72 | Simple CRUD endpoint (reusing existing pattern) |
| M    | 2             | 2                  |    60 |        100 |   160 | New model + service + repo + view + template |
| L    | 5             | 3                  |   155 |        250 |   410 | Cross-cutting feature (auth, search, export) |
| XL   | 8             | 5                  |   275 |        440 |   720 | Novel integration (external API, MCP server, async worker) |

Note: L and XL FP weights are lower than SP values because the client pays for delivered capability, not internal effort complexity. Complex cross-cutting work (auth, search) delivers 3 FP of value even if it takes 5 SP of effort.

**Calibration status:** SEED (not yet statistically validated — requires ≥ 3 completed sprints with token logs)

---

## 2. AI Productivity Adjustment Factor (PAF)

| AI Tier  | Model class    | PAF range | Notes |
|----------|----------------|-----------|-------|
| Tier 1   | Claude Sonnet 4+ | 1.3–1.5× | Primary coding model; context-rich sessions |
| Tier 2   | Claude Haiku 4+ | 1.1–1.3× | Fast iteration; lower context retention |
| Baseline | No AI / manual  | 1.0×     | Pure human baseline |

Applied as: `K_adjusted = K_seed / PAF` (fewer tokens needed because AI is more efficient)
**Default for Mimir stack:** PAF = 1.4× (Tier 1, established codebase context)

---

## 3. Client Pricing Model — AFP Formula

```
AFP = Σ FP × Stack Factor × Org Factor
Quote Total = AFP × $/FP
```

**What the client sees:** FP count, Stack Factor, Org Factor, $/FP rate, AFP total, and Total price.
**What the client never sees:** tokens, K values, ECF, TCF, SP, or internal calibration data.

ECF and TCF (Section 4 below) are internal multipliers that feed the $/FP calibration rate — they are not exposed on the quote. The Stack Factor and Org Factor encode the same real-world friction for the client but in commercially legible terms.

---

## 4. Stack Factor (Client-Facing)

Stack Factor reflects the technical complexity and risk of the client's technology environment. Applied per-project.

**Base tier:**

| Stack Factor | Description |
|:------------:|-------------|
| 0.85 | Greenfield project, single clean modern stack, no legacy constraints |
| 1.00 | Standard single stack (Django+HTMX, Rails, Node/Express, FastAPI) |
| 1.25 | Two integrated stacks (e.g., React SPA + REST API backend) |
| 1.50 | Legacy codebase integration (strangler-fig, adapter patterns) |
| 1.75 | Multi-cloud or platform-constrained deployment (GCP + AWS, etc.) |
| 2.00 | Enterprise platform (Salesforce, SAP, ServiceNow, SharePoint) |
| 2.50+ | Government / highly regulated system (FedRAMP, ITAR, FISMA) |

**Additive modifiers** (apply on top of base tier):

| Condition | Modifier |
|-----------|:--------:|
| On-premises deployment required | +0.10 |
| Legacy system integration (data migration, adapters) | +0.15 |
| Multi-cloud architecture | +0.15 |
| Real-time requirements (WebSockets, event streaming) | +0.10 |
| Mobile (iOS and/or Android) in scope | +0.20 |

Example: Standard stack (1.00) + legacy integration (+0.15) + on-premises (+0.10) = **Stack Factor 1.25**

---

## 5. Org Factor (Client-Facing)

Org Factor reflects the friction introduced by the client's organizational processes, approval chains, and compliance requirements. Applied per-project.

| Org Factor | Description |
|:----------:|-------------|
| 0.80 | Startup (1–5 people, flat structure, one decision-maker, no formal process) |
| 1.00 | Small team / SME (5–20 people, basic sprint process, PM involved) |
| 1.25 | Mid-size organization (20–100, defined SDLC, multiple stakeholders) |
| 1.50 | Enterprise (100+, formal change management, legal/security review gates) |
| 2.00 | ITIL/ITSM shop (CAB approvals, change freeze windows, ticketed releases) |
| 2.50 | Regulated enterprise (SOX, PCI-DSS, HIPAA — audit trails, sign-off requirements) |
| 3.50 | Government / public sector (procurement gates, FISMA/FedRAMP, multi-agency review) |

---

## 6. $/FP Calibration Rate

The $/FP rate is the internal bridge between token cost and client pricing. It is derived from actual sprint data and is updated after each sprint close.

| Status | $/FP Rate | How Set |
|--------|:---------:|---------|
| SEED | $250 | Pre-calibration default. Derived from $3/MTok × avg K per FP (≈ 83K/FP at M size). Use until 3 sprints complete. |
| CALIBRATED | actual | `$/FP_actual = total_api_cost_sprint / total_FP_delivered_sprint`. Weighted average over last 3–5 sprints. |

**$/FP is never shown to the client.** The client sees the AFP total and the total price. The $/FP rate is adjusted by finance/delivery after each sprint close via EST-08.

**Margin note:** $/FP SEED rate of $250 assumes ~3× markup over raw API cost. Adjust markup policy to match your business model.

---

## 7. BSP / DSP Overhead FP

Bootstrap (BSP) and Deploy Software Process (DSP) are quoted as a "Sprint 0 / Project Setup" line item on the client quote, separate from feature delivery FPs.

**FP weights for BSP activities** (Sprint 0):

| Activity | Size | FP |
|----------|:----:|---:|
| BSP-01 Verify/Install Prerequisites | XS | 0.5 |
| BSP-02 Initialize Repository | XS | 0.5 |
| BSP-03 Scaffold Project Structure | S | 1.0 |
| BSP-04 Initialize Runtimes/Dependencies | S | 1.0 |
| BSP-05 Configure Dev Tooling | M | 2.0 |
| BSP-06 Create Makefile | M | 2.0 |
| BSP-07 Create Welcome Page/Verify | S | 1.0 |
| BSP-08 Configure Observability/Logging | M | 2.0 |
| **BSP Total** | | **10.0 FP** |

**FP weights for DSP activities** (AI IDE configuration):

| Activity | Size | FP |
|----------|:----:|---:|
| DSP-01 Verify ESM Artifacts | XS | 0.5 |
| DSP-02 Verify DTA Artifacts | XS | 0.5 |
| DSP-03 Verify Architecture/Code Organization | S | 1.0 |
| DSP-04 Choose Target AI IDE | XS | 0.5 |
| DSP-05 Generate AI IDE Configuration | M | 2.0 |
| DSP-06 Review and Commit | XS | 0.5 |
| **DSP Total** | | **5.0 FP** |

**Combined Sprint 0 overhead: ~15 FP** (before Stack × Org adjustment).

On the client quote, show as: `Sprint 0 — Project Setup: 15 FP × Stack × Org × $/FP`

---

## 8. ECF / TCF Combined Multiplier — Internal (feeds $/FP calibration)

> **Internal use only.** ECF/TCF determine the internal token cost per FP, which feeds the $/FP calibration rate. These factors are never shown to the client — the Stack Factor and Org Factor capture the same reality in client-legible terms.

### Mimir MVP Actuals

**ECF** (Environmental Complexity Factor):

| Factor | Description | Rating | Weight | Contribution |
|--------|-------------|-------:|-------:|-------------:|
| E1 | Familiarity with used model | 4 | 1.5 | 6.0 |
| E2 | Application experience | 2 | 0.5 | 1.0 |
| E3 | OO experience | 4 | 1.0 | 4.0 |
| E4 | Lead analyst capability | 4 | 0.5 | 2.0 |
| E5 | Motivation | 5 | 1.0 | 5.0 |
| E6 | Stable requirements | 4 | 2.0 | 8.0 |
| E7 | Part-time workers | 5 | -1.0 | -5.0 |
| E8 | Difficult programming language | 4 | -1.0 | -4.0 |

`ECF = 1.4 + (−0.03 × 17.0) = 0.89`
AI extension (A1–A5 factors, sum = 17): `ECF_final = 0.89 × (1 − 0.08) = 0.82`

**TCF** (Technical Complexity Factor):

Sum of T1–T13 weighted ratings = 42.
`TCF = 0.6 + (0.01 × 42) = 1.02`

**Combined multiplier:** `0.82 × 1.02 = 0.87` ← favorable AI environment, use this for Mimir-like projects

---

## 9. Sizing Rules — v2 (Post-Calibration)

### v1 → v2 Changes
The root cause of Mimir estimation errors was using **scenario count as a proxy for implementation effort**. Scenarios measure *test breadth*, not *code complexity*.

| Pattern | v1 Rule | v2 Rule | Why changed |
|---------|---------|---------|-------------|
| 1st CRUD entity of a type | S → M | **S → M** (unchanged) | Correct — first instance is novel |
| 2nd–Nth CRUD entity (reusing pattern) | S → M | **XS → S** | Pattern reuse cuts effort dramatically |
| Novel cross-cutting feature | M → L | **M → L** (unchanged) | Cross-cutting features don't benefit from reuse |
| Config / bootstrap (settings, URLs, base templates) | S → M | **XS → S** | Code-light, config-heavy; was over-estimated in Auth/Setup (VF=0.39) |
| External integration (API client, MCP server) | M → L | **L → XL** | Integration uncertainty is real; MCP VF shows L underestimates |
| Feature sizing by scenario count | ❌ used | **❌ never use** | 10 scenarios ≠ 10× effort vs 1 scenario |

### Decision Tree for Sizing a Feature

```
Is this a completely new type of feature in the codebase?
├── YES → Is it cross-cutting or integration work?
│         ├── YES (cross-cutting) → L → XL
│         └── NO (new CRUD entity) → S → M
└── NO  → Does it reuse an established pattern (service/repo/template)?
          ├── YES → XS → S
          └── NO (new wrinkle on old pattern) → S → M
```

---

## 10. Mimir MVP Calibration Results

Measured from `main` branch, April 2026. LOC via `cloc`, 8 act groups.
**Calibration factor:** 0.10 K tokens / LOC (anchored on Activities act).

| Act Group | Est SP | Est K exp (K) | Actual LOC | Token Proxy (K) | VF | Status |
|-----------|-------:|--------------:|-----------:|----------------:|----:|--------|
| Auth / Setup | 3.0 | 135 | 1,765 | 177 | 1.30× | ~accurate |
| Playbooks | 27.0 | 1,790 | 3,372 | 337 | 0.19× | ❌ over-estimated 5× |
| Workflows | 13.0 | 910 | 2,996 | 300 | 0.33× | ❌ over-estimated 3× |
| **Activities** | **6.0** | **280** | **3,388** | **339** | **1.21×** | **✅ calibration anchor** |
| Artifacts | 15.0 | 720 | 2,654 | 265 | 0.37× | ❌ over-estimated 2.7× |
| Agents | 3.5 | 113 | 1,919 | 192 | 1.70× | ⚠ slightly under |
| Skills | 6.0 | 235 | 1,762 | 176 | 0.75× | ~accurate |
| MCP | 24.0 | 1,250 | 3,529 | 353 | 0.28× | ❌ over-estimated 3.6× |
| **TOTAL** | **114.5** | **6,433** | **25,885** | **2,588** | **0.40×** | |

**Summary:** Overall estimate was ~2.5× too high in SP terms. K-per-SP baselines appear reasonable; the problem was SP sizing.

### Root Cause

The Mimir estimation sized acts by counting scenarios per feature file (10 scenarios → large = L or XL). This is wrong because:

1. **Pattern reuse was ignored.** Playbooks, Activities, Workflows, Artifacts all implement the same Django pattern (Model + Admin + Repository + Service + View + Template + FAT). The 2nd–4th entity takes a fraction of the effort of the 1st.

2. **Scenario count ≠ implementation effort.** A feature with 10 edge-case scenarios tests one endpoint from many angles. It doesn't take 10× more code than a 1-scenario feature.

3. **K baselines are largely correct.** Activities VF = 1.21 and Auth/Setup VF = 1.30 confirm the K values for genuinely novel work are in the right range.

---

## 11. Sprint Actuals History

_Populate after each sprint close (EST-08)._

| Sprint | Planned SP | Actual SP | Planned K | Actual K (from token log) | VF | Date |
|--------|:----------:|:---------:|:---------:|:-------------------------:|:--:|------|
| — | — | — | — | — | — | — |

**Calibration threshold:** 3+ completed sprints with token logs → update status from SEED → CALIBRATED.

---

## 12. COCOMO Convergence (Schedule Uncertainty by Phase)

| Phase | Min bound | Max bound | Source |
|-------|:---------:|:---------:|--------|
| Initial concept | ×0.25 | ×4.0 | McConnell 1996, Table 5-2 |
| Approved product definition | ×0.5 | ×2.0 | ibid |
| Requirements complete | ×0.67 | ×1.5 | ibid |
| **Architecture complete** | **×0.80** | **×1.25** | ibid |
| Detailed design complete | ×0.90 | ×1.10 | ibid |

Mimir MVP ran EST at "Architecture complete" → P10/P90 range: ×0.80 to ×1.25 of P50.

---

## 13. McConnell Schedule Formula

```
Optimal schedule (calendar months) = 3.0 × (effort in person-months)^(1/3)
```

For AI-assisted single developer: `person-months = K_total / (throughput_K_per_month)`
Default Mimir throughput: 1,500 K tokens/day × 20 working days = 30,000 K/month.

Example at P50 = 18,200 K:
`person-months = 18,200 / 30,000 = 0.61`
`schedule = 3.0 × 0.61^(1/3) = 3.0 × 0.85 = 2.6 months ≈ 12 working days` ← matches simulation

---

## 14. BPE Artifact K Ranges (Django + HTMX Stack)

Token cost ranges for individual BPE artifacts, independent of SP sizing.

| Artifact | Small (K) | Medium (K) | Large (K) |
|----------|----------:|-----------:|----------:|
| Django Model + Admin | 8 | 15 | 28 |
| Repository methods | 5 | 10 | 20 |
| Service layer | 8 | 18 | 35 |
| Django View + URL | 6 | 12 | 22 |
| Unit + Integration Tests | 10 | 20 | 40 |
| Django Template + HTMX | 8 | 16 | 30 |
| Feature Acceptance Tests (FAT) | 8 | 15 | 28 |
| DoD checklist | 3 | 6 | 12 |
| E2E + PR | 6 | 12 | 22 |
| Implementation Plan | 5 | 8 | 15 |

Use these ranges for **Level 2 detailed estimates** (EST-06). Sum artifact estimates per feature and use PERT formula.

---

## 15. Notes and Open Questions

- [ ] Validate K baselines once 3 sprints have actual token logs (target: CALIBRATED status)
- [ ] Measure "pattern reuse discount" empirically: track tokens for 1st vs 2nd CRUD entity of same type
- [ ] Check if LOC proxy 0.10 K/LOC holds for non-Django stacks (React, FastAPI, etc.)
- [ ] The "17×" overestimate figures from pre-calibration analysis need reconciliation with 0.10 K/LOC factor — likely a different baseline was used (raw session tokens vs LOC proxy)

