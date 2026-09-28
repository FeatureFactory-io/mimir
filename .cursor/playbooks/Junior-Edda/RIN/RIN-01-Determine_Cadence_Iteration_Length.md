# Activity: Determine Cadence & Iteration Length

**Activity ID**: 553
**Order**: 1
**Phase**: Construction
**Dependencies**: Successor: Activity 554 (Set the Iteration Goal)

## Description

Determine Cadence & Iteration Length

## Guidance

## Objective

Choose the iteration length and collaboration cadence from current team evidence, then record the decision in `docs/project/iterations/<iteration_id>/ITERATION_FRAME.md`.

## Required inputs

- Approved `docs/project/CHARTER.md`, especially Team Roster, maturity classification, and maturity evidence.
- Delivery Management Assignment.
- Candidate start date and participant availability.

## Procedure

1. Enter the ADE's planning mode when available; otherwise write the execution plan before changing project state.
2. Validate the Charter's maturity assessment. If it is missing or older than one completed iteration, reassess it with the Delivery Manager and team and update the Charter before selecting cadence.
3. Apply the default mapping:
   - `L2` or `early-L3`: one-week iteration.
   - `late-L3` or `L4`: one-day iteration.
4. A different length is allowed only when the Delivery Manager records evidence and an expiry/review date.
5. For a one-person team, omit recurring meeting overhead; use asynchronous records and decision points. For larger teams, name only the ceremonies needed for coordination.
6. Create a stable `iteration_id` and record start/end timestamps, maturity/evidence, chosen length, ceremonies/triggers, participants, timezone, exception rationale, and approval.

## Completion evidence

The frame exists, the maturity evidence is current, the selected length is mechanically derived or explicitly justified, every ceremony has a purpose and owner, and the Delivery Manager approval is recorded.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

- **Cadence and Iteration Length by Team Maturity** (`cadence-and-iteration-length-by-team-maturity`)

## Artifacts Produced

- **Iteration Frame** (Document) - Required

## Artifacts Consumed

- **Delivery Management Assignment** (Document) - Required
- **Project Charter** (Document) - Required
- **Iteration Closeout** (Document) - Optional
- **Iteration Assessment Report** (Document) - Optional

## Notes

No additional notes.
