# Activity: Draft Charter v0

**Activity ID**: 548
**Order**: 3
**Phase**: Kickoff
**Dependencies**: Predecessor: Activity 547 (Absorb Vision/Scope Handover)
Successor: Activity 549 (Run ESM with Client, Walk Mockups)

## Description

Draft Charter v0

## Guidance

## Objective

Create the executable project-management contract at `docs/project/CHARTER.md` from the normalized handover. Charter v0 must be approved before Inception starts.

## Plan first

Enter the ADE's planning mode when available. Otherwise write a step-by-step drafting plan. Sections may be drafted in parallel only when each worker writes a separate section and one final worker checks cross-section consistency.

## Required structure

1. **Goals** — outcome, measure, target, target date, evidence source, owner.
2. **Team Roster** — person/agent, mission, authority, owned workflows/artifacts, meetings, backup. Include team maturity: `L2 | early-L3 | late-L3 | L4`, supporting evidence, assessor, and assessment date.
3. **Variables We Track** — one row per stable `variable_id` with definition, unit, source system, exact query/command, aggregation/window, freshness limit, Green/Yellow/Orange/Red or Green/Red thresholds, missing-data behavior, owner, and `gating_policy: observe | pause_new_work | block_release`.
4. **Artifact Coverage Decision** — artifact, required?, canonical path/system, owner, freshness rule, validation command.
5. **Cadence** — current iteration-length decision process, ceremonies, participants, trigger, duration; recurring meetings only when team size is greater than one.
6. **Release Roadmap** — alpha/beta/gamma/RC, explicitly marked aspirational until EST validates it.

## Procedure and gates

- Cite every statement back to the Vision/Scope Handover or label it as an assumption.
- Use stable IDs for variables and artifacts; display names may change without breaking history.
- Define `Unknown` handling separately from performance bands. Missing/stale evidence is never Green.
- Obtain explicit sponsor and Delivery Manager approval.

## Completion evidence

All six sections exist; every variable is mechanically measurable; every required artifact is locatable and testable; maturity has evidence; gating policies are explicit; the roadmap is labeled aspirational; approval and version `v0` are recorded.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

- **Charter Is Source of Truth for Variables** (`charter-is-source-of-truth-for-variables`)
- **Release Roadmap Is Aspirational** (`release-roadmap-is-aspirational`)

## Artifacts Produced

- **Project Charter** (Document) - Required

## Artifacts Consumed

- **Delivery Management Assignment** (Document) - Required
- **Vision/Scope Handover Package** (Document) - Required

## Notes

No additional notes.
