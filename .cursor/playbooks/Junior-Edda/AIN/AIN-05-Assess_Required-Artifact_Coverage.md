# Activity: Assess Required-Artifact Coverage

**Activity ID**: 564
**Order**: 5
**Phase**: Construction
**Dependencies**: Predecessor: Activity 560 (Open an Assessment Run)
Successor: Activity 562 (Reconcile Risk and Problem Tickets)

## Description

Assess Required-Artifact Coverage

## Guidance

## Objective

Verify the existence, validity, ownership, and freshness of every artifact the Charter marks required.

## Procedure

1. Read the required-artifact table from the Charter version in `RUN.md`.
2. If the ADE supports parallel workers, fan out one read-only worker per artifact. Each writes only `artifacts/<artifact_id>.json`.
3. For each artifact check its declared canonical path/system, validation command or schema, owner, version, freshness rule, and expected producer.
4. Record `present | missing | stale | invalid | inaccessible`; never infer coverage from a similarly named file.
5. Converge results into `ARTIFACT_COVERAGE.json` with covered/required counts, percentage when meaningful, missing/invalid list, evidence locations, and errors.
6. Do not create missing artifacts in this workflow; route remediation to RIN/backlog or a Project-Management Ticket according to Charter policy.

## Completion evidence

Every required artifact has one evidence-backed status from the shared snapshot; validation was executed where declared; gaps have owners or routing; and coverage is not overstated.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

- **Required-Artifact Coverage Report** (Document) - Required

## Artifacts Consumed

- **Project Charter** (Document) - Required
- **Assessment Run Record** (Document) - Required

## Notes

No additional notes.
