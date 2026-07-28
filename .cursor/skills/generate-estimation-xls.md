# Generate Estimation XLS

Python script for generating estimation spreadsheets.

```python
#!/usr/bin/env python3
"""
generate_estimation_xls.py  —  FeatureFactory EST Skill
========================================================
Produces docs/plans/ESTIMATION_TEMPLATE.xlsx (9 tabs, Monte Carlo, EBS charts)
from a project data dictionary.

Usage
-----
1. Fill in PROJECT_DATA below (Windsurf: run BPE-01 in estimation mode per
   scenario to get the wbs dict; use EST-03 sizing table for sizes).
2. Install dependency (once):  pip install xlsxwriter
3. Run:  python generate_estimation_xls.py

Called by Windsurf as part of the EST workflow. Can also be run standalone.

Tabs produced
-------------
  0-Client Quote      AFP pricing, delivery commitment bands
  1-Setup             Project params, reference story baselines
  2-Scenario List     All BDD scenarios with L1 sizing + adjusted K ranges
  3-ECF               Environmental Complexity Factors (internal)
  4-TCF               Technical Complexity Factors (internal)
  5-Rough Estimates   Sprint-level PERT totals (L1)
  6-Monte Carlo       10K-iteration simulation + EBS S-curve charts
  7-WBS Features      Per-artifact BPE-01 breakdown (L2, if wbs filled)
  8-Detailed Estimates L1/L2 cross-check per scenario
"""

import math
import random
import os
import xlsxwriter  # pip install xlsxwriter

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT_DATA  ←  WINDSURF FILLS THIS IN
# ══════════════════════════════════════════════════════════════════════════════
PROJECT_DATA = {
    # ── Identity ──────────────────────────────────────────────────────────────
    "project_name": "My Project — MVP v1",
    "output_path":  "docs/plans/ESTIMATION_TEMPLATE.xlsx",   # relative to repo root

    # ── Pricing parameters ────────────────────────────────────────────────────
    # stack_factor: 1.0 = standard single stack (Django+HTMX+SQLite)
    #               add +0.2 per extra stack tier (e.g. React FE, external API)
    "stack_factor":  1.0,
    "org_factor":    0.8,   # 0.8 solo dev  |  1.0 small team  |  1.2 large team
    "rate_per_fp":   250,   # $/FP  — SEED until calibrated after 3 sprints (EST-08)

    # ── Simulation parameters ─────────────────────────────────────────────────
    "sprint_days":      1,       # calendar days per sprint
    "throughput_k_day": 1500,    # K tokens per working day (from Setup tab calibration)
    "iterations":       10_000,
    "multiplier":       0.87,    # ECF×TCF combined — auto-computed from tabs 3/4 if left as None
                                 # set a float here to override (e.g. 0.87 for architecture-complete)

    # ── Scenarios ─────────────────────────────────────────────────────────────
    # EST-03 sizing:  XS=0.5SP  S=1SP  M=2SP  L=5SP  XL=8SP
    # Columns: (scenario_id, feature_file, act/group, description, size, sprint, notes)
    #
    # Anti-patterns to avoid:
    #   ✗  Size 2nd/3rd CRUD entity same as 1st — downgrade with reuse (XS→S, S→M)
    #   ✗  Size by scenario count — size by CODE complexity, not test count
    #   ✗  Size all config/nav as S — config-heavy work is XS
    "scenarios": [
        # ── EXAMPLE — replace with your project's scenarios ───────────────────
        # (sid,                    feature_file,        group,      description,                size, sprint, notes)
        ("PROJ-AUTH-01",           "auth.feature",      "Sprint 1", "Login / logout / session", "S",  1, "First auth entity — novel model+service"),
        ("PROJ-HOME-01",           "home.feature",      "Sprint 1", "Home dashboard",           "XS", 1, "Read-only, template-heavy"),
        ("PROJ-ITEM-LIST-01",      "items.feature",     "Sprint 1", "Item list + search",       "M",  1, "First CRUD entity — full BPE cycle"),
        ("PROJ-ITEM-CREATE-01",    "items.feature",     "Sprint 2", "Create item",              "M",  2, "New model + service"),
        ("PROJ-ITEM-EDIT-01",      "items.feature",     "Sprint 2", "Edit item",                "S",  2, "Reuses create pattern — EXTEND"),
        ("PROJ-ITEM-DELETE-01",    "items.feature",     "Sprint 2", "Delete item modal",        "S",  2, "Modal confirm — REUSE pattern"),
    ],

    # ── WBS (Level 2 — optional) ──────────────────────────────────────────────
    # Run BPE-01 in estimation mode (EST-06) for each scenario to get this list.
    # If a scenario SID is absent from wbs, L1 K-range is used for that scenario.
    #
    # Artifact types   K ranges (min/exp/max):
    #   Plan           5 / 8 / 15      — BPE-01 implementation plan
    #   Model          8 / 15 / 28     — Django model + admin
    #   Repo           5 / 10 / 20     — Repository methods
    #   Service        8 / 18 / 35     — Service layer business logic
    #   View           6 / 12 / 22     — Django view + URL pattern
    #   Template       8 / 16 / 30     — Django template (full page)
    #   Partial        4 / 8 / 15      — HTMX partial / reusable fragment
    #   Tests          10 / 20 / 40    — Unit + integration tests
    #   FAT            8 / 15 / 28     — Feature acceptance tests
    #   Journey        5 / 10 / 18     — Journey certification tests
    #   DoD            3 / 6 / 12      — DoD checklist (NEVER omit)
    #   E2E            6 / 12 / 22     — E2E Playwright tests + PR
    #
    # Reuse flags:
    #   NEW    → 1.0×   build from scratch
    #   EXTEND → 0.6×   existing code needs significant modification
    #   REUSE  → 0.3×   trivial wiring / config only
    "wbs": {
        "PROJ-AUTH-01": [
            ("Plan",     "BPE-01 implementation plan",            "NEW"),
            ("Model",    "User model (Django auth extension)",    "NEW"),
            ("Repo",     "UserRepo.authenticate / get_by_id",     "NEW"),
            ("Service",  "AuthService.login / logout / session",  "NEW"),
            ("View",     "LoginView / LogoutView + URL patterns",  "NEW"),
            ("Template", "login.html / logout confirmation",       "NEW"),
            ("Tests",    "Auth unit + integration tests",          "NEW"),
            ("FAT",      "Login / logout / session FAT",           "NEW"),
            ("DoD",      "DoD checklist",                          "NEW"),
            ("E2E",      "E2E Playwright: login flow",             "NEW"),
        ],
        "PROJ-ITEM-LIST-01": [
            ("Plan",     "BPE-01 implementation plan",            "NEW"),
            ("Model",    "Item model + admin",                     "NEW"),
            ("Repo",     "ItemRepo.list / filter / search",        "NEW"),
            ("Service",  "ItemService.get_list",                   "NEW"),
            ("View",     "ItemListView + URL",                     "NEW"),
            ("Template", "items/list.html",                        "NEW"),
            ("Tests",    "Item list unit + integration tests",     "NEW"),
            ("FAT",      "List + search FAT",                      "NEW"),
            ("DoD",      "DoD checklist",                          "NEW"),
            ("E2E",      "E2E Playwright: item list",              "NEW"),
        ],
        "PROJ-ITEM-CREATE-01": [
            ("Plan",     "BPE-01 implementation plan",            "NEW"),
            ("Model",    "Item model (extends List model)",        "EXTEND"),
            ("Repo",     "ItemRepo.create",                        "EXTEND"),
            ("Service",  "ItemService.create",                     "NEW"),
            ("View",     "ItemCreateView + URL",                   "NEW"),
            ("Template", "items/create.html",                      "NEW"),
            ("Tests",    "Create unit + integration tests",        "NEW"),
            ("FAT",      "Create item FAT",                        "NEW"),
            ("DoD",      "DoD checklist",                          "REUSE"),
            ("E2E",      "E2E Playwright: create item",            "NEW"),
        ],
        "PROJ-ITEM-EDIT-01": [
            ("Plan",     "BPE-01 implementation plan",            "REUSE"),
            ("Model",    "Item model (no change)",                 "REUSE"),
            ("Repo",     "ItemRepo.update",                        "EXTEND"),
            ("Service",  "ItemService.update",                     "NEW"),
            ("View",     "ItemEditView + URL",                     "EXTEND"),
            ("Template", "items/edit.html (reuses create form)",   "EXTEND"),
            ("Tests",    "Edit unit + integration tests",          "NEW"),
            ("FAT",      "Edit item FAT",                          "NEW"),
            ("DoD",      "DoD checklist",                          "REUSE"),
            ("E2E",      "E2E Playwright: edit item",              "NEW"),
        ],
        "PROJ-ITEM-DELETE-01": [
            ("Plan",     "BPE-01 implementation plan",            "REUSE"),
            ("Model",    "Item model (no change)",                 "REUSE"),
            ("Repo",     "ItemRepo.delete",                        "EXTEND"),
            ("Service",  "ItemService.delete",                     "NEW"),
            ("View",     "ItemDeleteView + URL",                   "REUSE"),
            ("Partial",  "delete_confirm_modal.html (REUSE)",      "REUSE"),
            ("Tests",    "Delete unit + integration tests",        "NEW"),
            ("FAT",      "Delete item FAT",                        "NEW"),
            ("DoD",      "DoD checklist",                          "REUSE"),
            ("E2E",      "E2E Playwright: delete item",            "NEW"),
        ],
        # "PROJ-HOME-01": [],  # omit or leave empty → L1 sizing used
    },

    # ── ECF ratings (0–5) ─────────────────────────────────────────────────────
    # Rate each factor for your team/project. Default 3 = neutral.
    "ecf_ratings": {
        "E1": 3,   # Familiarity with AI model/tooling   (high=good → +weight)
        "E2": 3,   # Part-time / context switching       (low=good → -weight)
        "E3": 3,   # Analyst / prompt engineering skill  (high=good → +weight)
        "E4": 3,   # Lead dev application experience     (high=good → +weight)
        "E5": 3,   # Team motivation                     (high=good → +weight)
        "E6": 3,   # Requirements stability              (high=good → +weight)
        "E7": 3,   # Part-time users / product owners    (low=good → -weight)
        "E8": 3,   # Difficulty of stack / language      (low=good → -weight)
        "A1": 3,   # AI model tier (Opus=5, Sonnet=3, Haiku=1)
        "A2": 3,   # Prompt maturity (mature BPE=4-5, first project=1-2)
        "A3": 3,   # Hallucination risk (well-known stack=4-5, novel=1-2)
        "A4": 3,   # Context window pressure (small features=4-5, huge=1-2)
        "A5": 3,   # AI code rework rate (41% baseline = 3)
    },

    # ── TCF ratings (0–5) ─────────────────────────────────────────────────────
    "tcf_ratings": {
        "T1": 2,   # Distributed / microservices  (monolith=1, full dist=5)
        "T2": 2,   # Response time / performance SLA
        "T3": 3,   # End-user efficiency / UX optimised
        "T4": 2,   # Complex internal algorithms
        "T5": 3,   # Code reusability requirement
        "T6": 3,   # Easy to install / deploy
        "T7": 3,   # Usability
        "T8": 2,   # Portability across platforms
        "T9": 4,   # Maintainability (methodology evolves)
        "T10": 1,  # Concurrent users / multi-tenant
        "T11": 2,  # Security requirements
        "T12": 2,  # Third-party / external API integration
        "T13": 2,  # Special user training required
    },

    # ── Calibration notes ─────────────────────────────────────────────────────
    "notes": [
        "SEED estimates — calibrate $/FP after Sprint 1 close via EST-08.",
        "Level 2 (WBS) populated for scenarios in wbs dict; others use L1 K-range.",
        "Rerun this script after each sprint close to update Monte Carlo.",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS  (derived — do not edit below unless you know what you're doing)
# ══════════════════════════════════════════════════════════════════════════════

# K-token PERT baselines per artifact type  (min, exp, max)
K_ART = {
    "Plan":    (5,   8,  15),
    "Model":   (8,  15,  28),
    "Repo":    (5,  10,  20),
    "Service": (8,  18,  35),
    "View":    (6,  12,  22),
    "Template":(8,  16,  30),
    "Partial": (4,   8,  15),
    "Tests":   (10, 20,  40),
    "FAT":     (8,  15,  28),
    "Journey": (5,  10,  18),
    "DoD":     (3,   6,  12),
    "E2E":     (6,  12,  22),
}

MULT_FLAG = {"NEW": 1.0, "EXTEND": 0.6, "REUSE": 0.3}

# L1 size → (sp, fp, kmin, kexp, kmax)
SIZE_TABLE = {
    "XS": (0.5, 0.5,  12,  22,  36),
    "S":  (1.0, 1.0,  25,  45,  72),
    "M":  (2.0, 2.0,  60, 100, 160),
    "L":  (5.0, 3.0, 155, 250, 410),
    "XL": (8.0, 5.0, 275, 440, 720),
}


def artifact_pert(atype, flag):
    """Return (min, exp, max) K-tokens for one artifact after reuse multiplier."""
    lo, mi, hi = K_ART[atype]
    m = MULT_FLAG[flag]
    return round(lo * m, 1), round(mi * m, 1), round(hi * m, 1)


def triangular_sample(lo, mi, hi):
    """Draw one sample from Triangular(lo, mi, hi)."""
    return random.triangular(lo, hi, mi)


def run_monte_carlo(sc_data, wbs, multiplier, throughput, iterations):
    """
    10K-iteration Monte Carlo over scenario PERT triplets.
    Returns list of 100 (probability%, K-tokens, days) sorted by K ascending.
    """
    results_k = []
    for _ in range(iterations):
        total_k = 0.0
        for sc in sc_data:
            sid = sc["sid"]
            arts = wbs.get(sid)
            if arts:
                # L2: sum artifact samples
                sc_k = sum(triangular_sample(*artifact_pert(a, f)) for _, a, f in
                           [(wp,) + (atype, flag) for wp, (atype, _, flag) in
                            enumerate(arts, 1)])
            else:
                # L1: sample from scenario PERT
                sc_k = triangular_sample(sc["kmin"], sc["kexp"], sc["kmax"])
            total_k += sc_k * multiplier
        results_k.append(total_k)

    results_k.sort()
    n = len(results_k)
    percentiles = []
    for i in range(1, 101):
        idx = max(0, min(n - 1, int(i / 100 * n) - 1))
        k = results_k[idx]
        days = k / throughput
        percentiles.append((i, round(k, 1), round(days, 3)))
    return percentiles


def build_sprint_summary(sc_data, multiplier, throughput):
    """Aggregate scenario data by sprint for Tab 5."""
    sprints = {}
    for sc in sc_data:
        sp_num = sc["sprint"]
        if sp_num not in sprints:
            sprints[sp_num] = {"scenarios": 0, "sp": 0, "fp": 0,
                               "kmin": 0, "kexp": 0, "kmax": 0}
        s = sprints[sp_num]
        s["scenarios"] += 1
        s["sp"]   += sc["sp"]
        s["fp"]   += sc["fp"]
        s["kmin"] += sc["kmin"] * multiplier
        s["kexp"] += sc["kexp"] * multiplier
        s["kmax"] += sc["kmax"] * multiplier
    rows = []
    for sp_num in sorted(sprints):
        s = sprints[sp_num]
        rows.append((
            sp_num, s["scenarios"], round(s["sp"], 1), round(s["fp"], 1),
            round(s["kmin"], 0), round(s["kexp"], 0), round(s["kmax"], 0),
            round(s["kmin"] / throughput, 2),
            round(s["kexp"] / throughput, 2),
            round(s["kmax"] / throughput, 2),
            round(s["fp"], 1),
            round(s["fp"] * 250, 0),
            "Architecture Complete", "SEED", "",
        ))
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# MAIN  — build workbook
# ══════════════════════════════════════════════════════════════════════════════
def main():
    pd   = PROJECT_DATA
    name = pd["project_name"]
    out  = pd["output_path"]
    os.makedirs(os.path.dirname(out) if os.path.dirname(out) else ".", exist_ok=True)

    stack    = pd["stack_factor"]
    org      = pd["org_factor"]
    rate     = pd["rate_per_fp"]
    mult     = pd["multiplier"] if pd["multiplier"] else 0.87
    thru     = pd["throughput_k_day"]
    iters    = pd["iterations"]
    ecf_r    = pd["ecf_ratings"]
    tcf_r    = pd["tcf_ratings"]

    # ── Enrich scenario list ───────────────────────────────────────────────────
    sc_data = []
    for sid, feat, grp, desc, size, sprint, notes in pd["scenarios"]:
        sp, fp, kmin, kexp, kmax = SIZE_TABLE[size]
        afp = round(fp * stack * org * rate, 0)
        # Apply multiplier to L1 K ranges
        sc_data.append({
            "sid": sid, "feat": feat, "grp": grp, "desc": desc,
            "size": size, "sprint": sprint, "notes": notes,
            "sp": sp, "fp": fp,
            "kmin": round(kmin * mult, 1),
            "kexp": round(kexp * mult, 1),
            "kmax": round(kmax * mult, 1),
            "afp": afp,
        })

    # Normalise wbs: each entry is (atype, desc, flag) tuple
    wbs = {}
    for sid, arts in pd["wbs"].items():
        wbs[sid] = [(atype, desc, flag) for atype, desc, flag in arts]

    # ── Run Monte Carlo ────────────────────────────────────────────────────────
    # For Monte Carlo L2 we need (atype, flag) only — strip desc
    wbs_mc = {sid: [(a, f) for a, _, f in arts] for sid, arts in wbs.items()}
    # Patch run_monte_carlo for wbs_mc format
    results_k = []
    random.seed(42)
    for _ in range(iters):
        total_k = 0.0
        for sc in sc_data:
            sid = sc["sid"]
            arts = wbs_mc.get(sid)
            if arts:
                sc_k = sum(triangular_sample(*artifact_pert(atype, flag))
                           for atype, flag in arts)
            else:
                sc_k = triangular_sample(sc["kmin"] / mult, sc["kexp"] / mult, sc["kmax"] / mult) * mult
            total_k += sc_k
        results_k.append(total_k)
    results_k.sort()
    n = len(results_k)
    pct = []
    for i in range(1, 101):
        idx = max(0, min(n - 1, int(i / 100 * n) - 1))
        k = results_k[idx]
        pct.append((i, round(k, 1), round(k / thru, 3)))

    sprint_rows = build_sprint_summary(sc_data, mult, thru)
    total_fp  = sum(sc["fp"]  for sc in sc_data)
    total_sp  = sum(sc["sp"]  for sc in sc_data)
    total_afp = round(total_fp * stack * org * rate, 0)

    # ── Workbook ───────────────────────────────────────────────────────────────
    wb = xlsxwriter.Workbook(out)

    def F(**kw):
        base = {"font_name": "Calibri", "font_size": 10}
        base.update(kw)
        return wb.add_format(base)

    # Formats
    fHdr  = F(bold=True, font_size=12, font_color="white",  bg_color="#1B4332", align="center", border=1)
    fSub  = F(bold=True, font_color="white",  bg_color="#2D6A4F", align="center", border=1)
    fBold = F(bold=True, border=1)
    fData = F(border=1)
    fDataR= F(border=1, align="right")
    fNum  = F(border=1, align="right", num_format="#,##0.0")
    fDol  = F(border=1, align="right", num_format="$#,##0")
    fTot  = F(bold=True, font_color="white", bg_color="#1B4332", border=1, align="right", num_format="#,##0.0")
    fTotL = F(bold=True, font_color="white", bg_color="#1B4332", border=1)
    fTotD = F(bold=True, font_color="white", bg_color="#1B4332", border=1, align="right", num_format="$#,##0")
    fWrap = F(border=1, text_wrap=True)
    fXS   = F(border=1, bg_color="#F0FFF4")
    fS    = F(border=1, bg_color="#D1FAE5")
    fM    = F(border=1, bg_color="#A7F3D0")
    fL    = F(border=1, bg_color="#6EE7B7")
    fNew  = F(border=1, bg_color="#FFF3CD", align="center")
    fExt  = F(border=1, bg_color="#D1ECF1", align="center")
    fReu  = F(border=1, bg_color="#D4EDDA", align="center")
    fNumN = F(border=1, align="right", num_format="#,##0.0", bg_color="#FFF3CD")
    fNumE = F(border=1, align="right", num_format="#,##0.0", bg_color="#D1ECF1")
    fNumR = F(border=1, align="right", num_format="#,##0.0", bg_color="#D4EDDA")
    fRowN = F(border=1, bg_color="#FFF3CD")
    fRowE = F(border=1, bg_color="#D1ECF1")
    fRowR = F(border=1, bg_color="#D4EDDA")
    fSub7 = F(bold=True, border=1, bg_color="#E8F5E9")
    fSub7R= F(bold=True, border=1, bg_color="#E8F5E9", align="right", num_format="#,##0.0")
    fEBS  = F(bold=True, font_color="white", bg_color="#048A81", align="center", border=1)
    fGreen = F(border=1, align="right", num_format="#,##0.0", bg_color="#E8F5E9")
    fAmber = F(border=1, align="right", num_format="#,##0.0", bg_color="#FFF3E0")
    fRed   = F(border=1, align="right", num_format="#,##0.0", bg_color="#FFEBEE")
    fGreenI= F(border=1, align="right", bg_color="#E8F5E9")
    fAmberI= F(border=1, align="right", bg_color="#FFF3E0")
    fRedI  = F(border=1, align="right", bg_color="#FFEBEE")

    SIZE_FMT = {"XS": fXS, "S": fS, "M": fM, "L": fL, "XL": fL}
    NUM_FMT  = {s: F(border=1, align="right", num_format="#,##0.0",
                     bg_color={"XS":"#F0FFF4","S":"#D1FAE5","M":"#A7F3D0",
                               "L":"#6EE7B7","XL":"#6EE7B7"}[s]) for s in SIZE_TABLE}
    FLAG_ROW = {"NEW": (fRowN, fNumN, fNew), "EXTEND": (fRowE, fNumE, fExt), "REUSE": (fRowR, fNumR, fReu)}

    # ── TAB 0  Client Quote ────────────────────────────────────────────────────
    ws0 = wb.add_worksheet("0-Client Quote")
    ws0.set_column("A:A", 28); ws0.set_column("B:B", 14); ws0.set_column("C:C", 55)
    ws0.set_row(0, 24)
    ws0.merge_range("A1:C1", f"{name} — Client Quote  (AFP × $/FP)", fHdr)
    ws0.write("A3", "A. PRICING PARAMETERS", fBold)
    ws0.write_row("A4", ["Parameter", "Value", "Description / Source"], fSub)
    p_rows = [
        ("Stack Factor",      stack,    "1.0 = standard single stack (Django+HTMX+SQLite)"),
        ("Org Factor",        org,      "0.8 solo  |  1.0 small team  |  1.2 large team"),
        ("$/FP Rate",         rate,     "SEED — update after 3 sprints via EST-08"),
        ("$/FP Status",       "SEED",   "Change to CALIBRATED after 3 sprints of actuals"),
    ]
    for i, (a, b, c) in enumerate(p_rows, 5):
        ws0.write(i, 0, a, fData); ws0.write(i, 1, b, fDataR); ws0.write(i, 2, c, fData)
    ws0.write("A10", "B. QUOTE SUMMARY  (AFP = FP × Stack × Org)", fBold)
    ws0.write_row("A11", ["Line Item", "FP", "Stack×Org", "AFP", "$ Total (AFP × $/FP)"], fSub)
    ws0.write("A12", "Sprint 0 — Project Setup (BSP+DSP)", fData)
    ws0.write("B12", 15, fDataR); ws0.write("C12", round(stack * org, 2), fDataR)
    sprint0_afp = round(15 * stack * org, 1)
    ws0.write("D12", sprint0_afp, fDataR); ws0.write("E12", round(sprint0_afp * rate, 0), fDol)
    ws0.write("A13", "Feature Delivery (from Scenario List)", fData)
    ws0.write("B13", round(total_fp, 1), fDataR); ws0.write("C13", round(stack * org, 2), fDataR)
    feat_afp = round(total_fp * stack * org, 1)
    ws0.write("D13", feat_afp, fDataR); ws0.write("E13", round(feat_afp * rate, 0), fDol)
    ws0.write("A14", "PROJECT TOTAL", fBold)
    ws0.write("B14", round(total_fp + 15, 1), fDataR); ws0.write("C14", round(stack * org, 2), fDataR)
    total_proj_afp = sprint0_afp + feat_afp
    ws0.write("D14", round(total_proj_afp, 1), fDataR)
    ws0.write("E14", round(total_proj_afp * rate, 0), fDol)
    ws0.write("A16", "C. DELIVERY COMMITMENT BANDS  (from Monte Carlo — EST-07)", fBold)
    ws0.write_row("A17", ["Percentile", "AFP", "$ Total", "K Tokens", "Duration (days)"], fSub)
    p10k, p50k, p80k, p95k = pct[9][1], pct[49][1], pct[79][1], pct[94][1]
    p10d, p50d, p80d, p95d = pct[9][2], pct[49][2], pct[79][2], pct[94][2]
    for i, (label, k, d) in enumerate([
        ("P10",               p10k, p10d),
        ("P50 — Median ★",    p50k, p50d),
        ("P80 — Planning ★★", p80k, p80d),
        ("P95 — Conservative",p95k, p95d),
    ], 18):
        ratio = k / p50k if p50k else 1
        band_afp = round(feat_afp * ratio, 1)
        ws0.write(i, 0, label, fData); ws0.write(i, 1, band_afp, fDataR)
        ws0.write(i, 2, round(band_afp * rate, 0), fDol)
        ws0.write(i, 3, round(k, 0), fDataR); ws0.write(i, 4, round(d, 2), fDataR)
    ws0.write("A23", "D. NOTES", fBold)
    for i, note in enumerate(pd["notes"], 24):
        ws0.write(i, 0, note, fWrap)

    # ── TAB 1  Setup ───────────────────────────────────────────────────────────
    ws1 = wb.add_worksheet("1-Setup")
    ws1.set_column("A:A", 30); ws1.set_column("B:H", 14)
    ws1.merge_range("A1:H1", f"{name} — Setup & Calibration", fHdr)
    ws1.write("A3", "A. PROJECT PARAMETERS", fBold)
    sp_params = [
        ("Project Name",            name),
        ("Sprint Duration (days)",  pd["sprint_days"]),
        ("Daily Throughput (K/day)",thru),
        ("AI Model",                "Claude Sonnet 4.x"),
        ("ECF×TCF Combined Mult.",  mult),
        ("$/FP Rate",               rate),
        ("Stack Factor",            stack),
        ("Org Factor",              org),
        ("Estimation Phase",        "Architecture Complete"),
        ("Iterations (Monte Carlo)",iters),
    ]
    for i, (k, v) in enumerate(sp_params, 4):
        ws1.write(i, 0, k, fData); ws1.write(i, 1, v, fData if isinstance(v, str) else fDataR)
    ws1.write("A15", "B. REFERENCE STORY BASELINES", fBold)
    ws1.write_row("A16", ["Size", "SP (internal)", "FP (client)",
                          "K Min", "K Exp", "K Max", "Status", "Notes"], fSub)
    ref_notes = {
        "XS": "Simple modal, inline form, config entry",
        "S":  "Single CRUD screen, service+repo+view+tests",
        "M":  "Full BPE cycle, first-time entity or novel component",
        "L":  "Cross-cutting / network integration",
        "XL": "Complex subsystem — split into L if possible",
    }
    for i, (sz, (sp, fp, kmin, kexp, kmax)) in enumerate(SIZE_TABLE.items(), 17):
        ws1.write_row(i, 0, [sz, sp, fp, kmin, kexp, kmax, "SEED", ref_notes[sz]], fData)

    # ── TAB 2  Scenario List ───────────────────────────────────────────────────
    ws2 = wb.add_worksheet("2-Scenario List")
    ws2.set_column("A:A", 20); ws2.set_column("B:B", 28)
    ws2.set_column("C:C", 10); ws2.set_column("D:D", 40)
    ws2.set_column("E:E", 6);  ws2.set_column("F:G", 8)
    ws2.set_column("H:M", 10); ws2.set_column("N:N", 8); ws2.set_column("O:O", 35)
    ws2.merge_range("A1:O1", f"{name} — Scenario List ({len(sc_data)} scenarios)", fHdr)
    ws2.write_row("A2", ["Scenario ID", "Feature", "Group", "Description", "Size",
                         "SP", "FP", "K Min", "K Exp", "K Max",
                         "Adj Min", "Adj Exp", "Adj Max", "Sprint", "Notes"], fSub)
    for i, sc in enumerate(sc_data):
        r = i + 2
        sf = SIZE_FMT.get(sc["size"], fData)
        nf = NUM_FMT.get(sc["size"], fDataR)
        sp, fp, kmin, kexp, kmax = SIZE_TABLE[sc["size"]]
        ws2.write(r, 0, sc["sid"], sf); ws2.write(r, 1, sc["feat"], sf)
        ws2.write(r, 2, sc["grp"], sf); ws2.write(r, 3, sc["desc"], sf)
        ws2.write(r, 4, sc["size"], sf)
        ws2.write(r, 5, sp, nf);  ws2.write(r, 6, fp, nf)
        ws2.write(r, 7, kmin, nf); ws2.write(r, 8, kexp, nf); ws2.write(r, 9, kmax, nf)
        ws2.write(r, 10, sc["kmin"], nf); ws2.write(r, 11, sc["kexp"], nf)
        ws2.write(r, 12, sc["kmax"], nf)
        ws2.write(r, 13, sc["sprint"], nf); ws2.write(r, 14, sc["notes"], sf)
    ws2.freeze_panes(2, 0)

    # ── TAB 3  ECF ─────────────────────────────────────────────────────────────
    ECF_FACTORS = [
        ("E1", "Familiarity with AI model/tooling",        1.5),
        ("E2", "Part-time / context switching",           -1.0),
        ("E3", "Analyst/prompt engineering experience",    0.5),
        ("E4", "Lead developer application experience",    0.5),
        ("E5", "Team motivation",                          1.0),
        ("E6", "Requirements stability",                   2.0),
        ("E7", "Part-time users/product owners",          -1.0),
        ("E8", "Difficulty of stack/language",            -1.0),
        ("A1", "AI model tier (Opus=5, Sonnet=3, Haiku=1)", 0.8),
        ("A2", "Prompt maturity (mature=5, first=1)",       0.6),
        ("A3", "Hallucination risk (low=5, high=1)",       -0.5),
        ("A4", "Context window pressure (large=5)",        -0.4),
        ("A5", "AI code rework rate (41% baseline=3)",     -0.6),
    ]
    ws3 = wb.add_worksheet("3-ECF")
    ws3.set_column("A:B", 30); ws3.set_column("C:E", 12); ws3.set_column("F:F", 45)
    ws3.merge_range("A1:F1", "Environmental Complexity Factors (ECF) — INTERNAL", fHdr)
    ws3.write("A2", "INTERNAL: ECF feeds combined multiplier (token budget). Never shown to client.", fWrap)
    ws3.write_row("A3", ["#", "Factor", "Weight", "Rating (0–5)", "Weighted", "Notes"], fSub)
    for i, (num, factor, weight) in enumerate(ECF_FACTORS, 4):
        rating = ecf_r.get(num, 3)
        ws3.write(i, 0, num, fData); ws3.write(i, 1, factor, fData)
        ws3.write(i, 2, weight, fDataR); ws3.write(i, 3, rating, fDataR)
        ws3.write(i, 4, f"=C{i+1}*D{i+1}", fDataR)
        ws3.write(i, 5, f"Rating={rating}", fData)
    # Rows 17–19 (0-indexed) = Excel rows 18–20
    ws3.write(17, 0, "ECF Base",              fBold); ws3.write(17, 1, "=1.4+(-0.03*SUM(E5:E12))", fDataR)
    ws3.write(18, 0, "AI Adjustment",         fBold); ws3.write(18, 1, "=1+(0.05*SUM(E13:E17))",   fDataR)
    ws3.write(19, 0, "ECF Final = Base × AI", fBold); ws3.write(19, 1, "=B18*B19",                 fDataR)

    # ── TAB 4  TCF ─────────────────────────────────────────────────────────────
    TCF_FACTORS = [
        ("T1",  "Distributed system / microservices",      2.0),
        ("T2",  "Response time / performance requirements", 1.0),
        ("T3",  "End-user efficiency (UX optimised)",       1.0),
        ("T4",  "Complex internal processing / algorithms", 1.0),
        ("T5",  "Code reusability requirement",             1.0),
        ("T6",  "Easy to install / deploy",                 0.5),
        ("T7",  "Easy to use (usability)",                  0.5),
        ("T8",  "Portability across platforms",             2.0),
        ("T9",  "Maintainability",                          1.0),
        ("T10", "Concurrent use / multi-user",              1.0),
        ("T11", "Security features",                        1.0),
        ("T12", "Third-party API / direct access",          1.0),
        ("T13", "Special user training required",           1.0),
    ]
    ws4 = wb.add_worksheet("4-TCF")
    ws4.set_column("A:B", 30); ws4.set_column("C:E", 12); ws4.set_column("F:F", 45)
    ws4.merge_range("A1:F1", "Technical Complexity Factors (TCF) — INTERNAL", fHdr)
    ws4.write("A2", "INTERNAL: TCF feeds combined multiplier. Client complexity → Stack Factor (Tab 0).", fWrap)
    ws4.write_row("A3", ["#", "Factor", "Weight", "Rating (0–5)", "Weighted", "Notes"], fSub)
    for i, (num, factor, weight) in enumerate(TCF_FACTORS, 4):
        rating = tcf_r.get(num, 3)
        ws4.write(i, 0, num, fData); ws4.write(i, 1, factor, fData)
        ws4.write(i, 2, weight, fDataR); ws4.write(i, 3, rating, fDataR)
        ws4.write(i, 4, f"=C{i+1}*D{i+1}", fDataR)
        ws4.write(i, 5, f"Rating={rating}", fData)
    # TCF Final at row 17 (0-indexed) = Excel row 18; factors in Excel rows 5–17
    ws4.write(17, 0, "TCF Final",                  fBold); ws4.write(17, 1, "=0.6+(0.01*SUM(E5:E17))", fDataR)
    ws4.write(18, 0, "ECF Final (from ECF tab)",   fBold); ws4.write(18, 1, "='3-ECF'!B20",            fDataR)
    ws4.write(19, 0, "Combined Multiplier ECF×TCF",fBold); ws4.write(19, 1, "=B18*B19",                fDataR)

    # ── TAB 5  Rough Estimates ─────────────────────────────────────────────────
    ws5 = wb.add_worksheet("5-Rough Estimates")
    ws5.set_column("A:A", 8); ws5.set_column("B:L", 12); ws5.set_column("M:O", 18)
    ws5.merge_range("A1:O1", f"{name} — Rough Estimates (L1 Token Budget + AFP Preview)", fHdr)
    ws5.write_row("A2", ["Sprint", "Scenarios", "SP", "FP",
                         "Min K", "Exp K", "Max K",
                         "Min d", "Exp d", "Max d",
                         "AFP", "AFP $", "Phase", "Calib", "Notes"], fSub)
    tot = dict(sc=0, sp=0, fp=0, kmin=0, kexp=0, kmax=0)
    for i, row in enumerate(sprint_rows, 3):
        ws5.write_row(i, 0, row, fData)
        tot["sc"]   += row[1]; tot["sp"]   += row[2]; tot["fp"]   += row[3]
        tot["kmin"] += row[4]; tot["kexp"] += row[5]; tot["kmax"] += row[6]
    tr = len(sprint_rows) + 3
    ws5.write(tr, 0, "TOTAL", fTotL)
    for c in range(1, 15): ws5.write(tr, c, "", fTot)
    ws5.write(tr, 1, tot["sc"],   fTot); ws5.write(tr, 2, round(tot["sp"], 1), fTot)
    ws5.write(tr, 3, round(tot["fp"], 1), fTot)
    ws5.write(tr, 4, round(tot["kmin"], 0), fTot); ws5.write(tr, 5, round(tot["kexp"], 0), fTot)
    ws5.write(tr, 6, round(tot["kmax"], 0), fTot)

    # ── TAB 6  Monte Carlo ────────────────────────────────────────────────────
    ws6 = wb.add_worksheet("6-Monte Carlo")
    ws6.set_column("A:A", 6); ws6.set_column("B:B", 16)
    ws6.set_column("C:C", 22); ws6.set_column("D:D", 18)
    ws6.merge_range("A1:D1",
        f"EBS SIMULATION DATA — 100-percentile distribution "
        f"({iters:,} iterations · triangular dist · {len(sc_data)} scenarios)", fEBS)
    ws6.write_row("A2", ["#", "Probability (%)", "Token Budget (K)", "Duration (days)"], fSub)
    for i, (p, k, d) in enumerate(pct):
        r = i + 2
        if p <= 50:  fi, fn = fGreenI, fGreen
        elif p <= 80: fi, fn = fAmberI, fAmber
        else:         fi, fn = fRedI,   fRed
        ws6.write(r, 0, i + 1, fi); ws6.write(r, 1, p, fi)
        ws6.write(r, 2, k, fn); ws6.write(r, 3, d, fn)
    # Summary block
    for j, (label, pidx) in enumerate([("P10",9),("P50",49),("P80",79),("P95",94)], 103):
        ws6.write(j, 0, label, fBold)
        ws6.write(j, 1, round(pct[pidx][1], 0), fNum)
        ws6.write(j, 2, round(pct[pidx][2], 2), fNum)

    # Token Budget S-curve
    max_k = math.ceil(max(p[1] for p in pct) / 1000) * 1000
    ch_k = wb.add_chart({"type": "line"})
    ch_k.add_series({
        "name": "Token Budget",
        "categories": ["6-Monte Carlo", 2, 1, 101, 1],
        "values":     ["6-Monte Carlo", 2, 2, 101, 2],
        "line": {"color": "#048A81", "width": 2},
        "marker": {"type": "none"}, "smooth": True,
    })
    ch_k.set_title({"name": "Token Budget S-Curve  (EBS — internal)"})
    ch_k.set_x_axis({"name": "Probability (%)", "min": 0, "max": 100, "major_gridlines": {"visible": True}})
    ch_k.set_y_axis({"name": "K Tokens", "min": 0, "max": max_k,      "major_gridlines": {"visible": True}})
    ch_k.set_legend({"none": True}); ch_k.set_size({"width": 480, "height": 300})
    ws6.insert_chart("F2", ch_k)

    # Duration S-curve
    ch_d = wb.add_chart({"type": "line"})
    ch_d.add_series({
        "name": "Duration",
        "categories": ["6-Monte Carlo", 2, 1, 101, 1],
        "values":     ["6-Monte Carlo", 2, 3, 101, 3],
        "line": {"color": "#F4A261", "width": 2},
        "marker": {"type": "none"}, "smooth": True,
    })
    ch_d.set_title({"name": "Duration S-Curve  (EBS — internal)"})
    ch_d.set_x_axis({"name": "Probability (%)", "min": 0, "max": 100, "major_gridlines": {"visible": True}})
    ch_d.set_y_axis({"name": "Duration (days)", "min": 0,             "major_gridlines": {"visible": True}})
    ch_d.set_legend({"none": True}); ch_d.set_size({"width": 480, "height": 300})
    ws6.insert_chart("F26", ch_d)

    # ── TAB 7  WBS Features ────────────────────────────────────────────────────
    ws7 = wb.add_worksheet("7-WBS Features")
    ws7.set_column("A:A", 20); ws7.set_column("B:B", 28)
    ws7.set_column("C:C", 7);  ws7.set_column("D:D", 5)
    ws7.set_column("E:E", 38); ws7.set_column("F:F", 10)
    ws7.set_column("G:G", 8);  ws7.set_column("H:H", 8); ws7.set_column("I:K", 9)
    ws7.set_column("L:L", 35)
    ws7.merge_range("A1:L1", "Work Breakdown Structure — BPE-01 Estimation Mode (EST-06)", fHdr)
    ws7.write_row("A2", ["Scenario ID", "Feature", "Sprint", "WP#",
                         "Artifact (BPE-01)", "Type", "Flag", "Reuse×",
                         "K Min", "K Exp", "K Max", "Notes"], fSub)
    row7 = 2
    wbs_totals = {}
    for sc in sc_data:
        sid = sc["sid"]
        arts = wbs.get(sid, [])
        sc_lo = sc_mi = sc_hi = 0.0
        for wp, (atype, desc, flag) in enumerate(arts, 1):
            lo, mi, hi = artifact_pert(atype, flag)
            sc_lo += lo; sc_mi += mi; sc_hi += hi
            fr, fn, ff = FLAG_ROW[flag]
            ws7.write(row7, 0, sid,           fr); ws7.write(row7, 1, sc["feat"],    fr)
            ws7.write(row7, 2, sc["sprint"],  fr); ws7.write(row7, 3, wp,            fr)
            ws7.write(row7, 4, desc,          fr); ws7.write(row7, 5, atype,         fr)
            ws7.write(row7, 6, flag,          ff); ws7.write(row7, 7, MULT_FLAG[flag], fn)
            ws7.write(row7, 8, lo,            fn); ws7.write(row7, 9, mi,            fn)
            ws7.write(row7, 10, hi,           fn)
            ws7.write(row7, 11, f"BPE-01 est. · {atype} · {flag}", fr)
            ws7.set_row(row7, 14); row7 += 1
        # sub-total row
        l1exp = sc["kexp"]
        delta = (sc_mi - l1exp) / l1exp if l1exp else 0
        warn  = "  ⚠️ WARNING >30%" if abs(delta) > 0.30 else ""
        note  = f"L1={l1exp}K  L2={sc_mi:.0f}K  Δ={delta:+.0%}{warn}"
        if arts:
            ws7.write(row7, 0,  f"  ▶ {sid} total", fSub7)
            for c in range(1, 8): ws7.write(row7, c, "", fSub7)
            ws7.write(row7, 8,  round(sc_lo, 1), fSub7R)
            ws7.write(row7, 9,  round(sc_mi, 1), fSub7R)
            ws7.write(row7, 10, round(sc_hi, 1), fSub7R)
            ws7.write(row7, 11, note,             fSub7)
            ws7.set_row(row7, 14); row7 += 1
        wbs_totals[sid] = (round(sc_lo, 1), round(sc_mi, 1), round(sc_hi, 1))
    ws7.freeze_panes(2, 0)

    # ── TAB 8  Detailed Estimates ──────────────────────────────────────────────
    ws8 = wb.add_worksheet("8-Detailed Estimates")
    ws8.set_column("A:A", 20); ws8.set_column("B:B", 28)
    ws8.set_column("C:F", 7);  ws8.set_column("G:K", 10)
    ws8.set_column("L:M", 10); ws8.set_column("N:N", 12)
    ws8.set_column("O:P", 10); ws8.set_column("Q:Q", 35)
    ws8.merge_range("A1:Q1",
        "Detailed Estimates — L2 vs L1 Cross-Check (EST-06 · rebaseline after each sprint close)", fHdr)
    ws8.write_row("A2", ["Scenario ID", "Feature", "Sprint", "Size", "SP", "FP",
                         "L2 Min(K)", "L2 Exp(K)", "L2 Max(K)", "L1 Exp(K)", "L1/L2 Δ%",
                         "Actual(K)", "Token VF", "AFP Est($)", "AFP VF", "Status", "Notes"], fSub)
    grand = dict(l2min=0, l2exp=0, l2max=0, l1exp=0, fp=0, afp=0)
    for i, sc in enumerate(sc_data):
        r = i + 2
        sf = SIZE_FMT.get(sc["size"], fData)
        nf = NUM_FMT.get(sc["size"], fDataR)
        l2lo, l2mi, l2hi = wbs_totals.get(sc["sid"], (sc["kmin"], sc["kexp"], sc["kmax"]))
        l1exp = sc["kexp"]; afp = sc["afp"]
        delta = (l2mi - l1exp) / l1exp if l1exp else 0
        if abs(delta) > 0.30: note = f"Δ={delta:+.0%} ⚠️ WARNING >30%"
        elif abs(delta) > 0.15: note = f"Δ={delta:+.0%} — review"
        else: note = f"Δ={delta:+.0%} — consistent"
        delta_fmt = F(border=1, align="right", num_format="0%",
                      bg_color="#F0FFF4" if abs(delta) <= 0.15 else
                               "#FFF3CD" if abs(delta) <= 0.30 else "#FFEBEE")
        ws8.write(r, 0,  sc["sid"],   sf); ws8.write(r, 1,  sc["feat"],   sf)
        ws8.write(r, 2,  sc["sprint"],nf); ws8.write(r, 3,  sc["size"],   sf)
        ws8.write(r, 4,  sc["sp"],    nf); ws8.write(r, 5,  sc["fp"],     nf)
        ws8.write(r, 6,  l2lo,        nf); ws8.write(r, 7,  l2mi,         nf)
        ws8.write(r, 8,  l2hi,        nf); ws8.write(r, 9,  l1exp,        nf)
        ws8.write(r, 10, delta,        delta_fmt)
        ws8.write(r, 11, "",          fData); ws8.write(r, 12, "",         fData)
        ws8.write(r, 13, afp,         fDol)
        ws8.write(r, 14, "",          fData); ws8.write(r, 15, "PLANNED",  sf)
        ws8.write(r, 16, note,        fWrap)
        ws8.set_row(r, 15)
        grand["l2min"] += l2lo; grand["l2exp"] += l2mi; grand["l2max"] += l2hi
        grand["l1exp"] += l1exp; grand["fp"] += sc["fp"]; grand["afp"] += afp
    tr = len(sc_data) + 2
    ws8.write(tr, 0, "TOTAL", fTotL)
    for c in range(1, 17): ws8.write(tr, c, "", fTot)
    ws8.write(tr, 5,  round(grand["fp"],   1), fTot)
    ws8.write(tr, 6,  round(grand["l2min"],1), fTot)
    ws8.write(tr, 7,  round(grand["l2exp"],1), fTot)
    ws8.write(tr, 8,  round(grand["l2max"],1), fTot)
    ws8.write(tr, 9,  round(grand["l1exp"],1), fTot)
    ws8.write(tr, 13, round(grand["afp"],  0), fTotD)
    ws8.set_row(tr, 18); ws8.freeze_panes(2, 0)

    wb.close()

    # ── Summary ────────────────────────────────────────────────────────────────
    l1_total = grand["l1exp"]
    l2_total = grand["l2exp"]
    delta_pct = (l2_total - l1_total) / l1_total * 100 if l1_total else 0
    print(f"\n✅  Written: {out}")
    print(f"   Scenarios  : {len(sc_data)}")
    print(f"   WBS rows   : {row7 - 2}")
    print(f"   L1 total   : {l1_total:,.0f} K")
    print(f"   L2 total   : {l2_total:,.0f} K   Δ={delta_pct:+.1f}%")
    print(f"   FP total   : {grand['fp']:.1f}   AFP: ${grand['afp']:,.0f}")
    print(f"   EBS P50    : {pct[49][1]:,.0f} K / {pct[49][2]:.2f} d")
    print(f"   EBS P80    : {pct[79][1]:,.0f} K / {pct[79][2]:.2f} d")
    print(f"   EBS P95    : {pct[94][1]:,.0f} K / {pct[94][2]:.2f} d")


if __name__ == "__main__":
    main()

```
