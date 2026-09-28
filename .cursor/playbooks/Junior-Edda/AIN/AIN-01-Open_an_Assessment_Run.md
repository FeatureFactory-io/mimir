# Activity: Open an Assessment Run

**Activity ID**: 560
**Order**: 1
**Phase**: Construction
**Dependencies**: Successor: Activity 564 (Assess Required-Artifact Coverage)

## Description

Open an Assessment Run

## Guidance

## Objective

Create one traceable, immutable assessment snapshot without interfering with delivery work.

## Required inputs

- Project Charter and Delivery Management Assignment.
- Huginn Assessment Contract.
- Project/repository/environment identity and the current iteration ID when one exists.

## Procedure

1. Validate that every tracked Charter variable has a stable `variable_id`, source, exact query/command, window, freshness limit, bands, Unknown behavior, owner, and gating policy.
2. Acquire the project assessment lock. If another run is active, return its run ID or wait according to the Huginn contract; never create overlapping side effects.
3. Create `run_id = AIN-<UTC timestamp>` and directory `docs/project/assessments/<run_id>/`.
4. Establish one snapshot boundary: repository revision, environment, iteration ID, source-system timestamps/cursors, Charter version, and artifact inventory timestamp.
5. Write `RUN.md` with trigger, initiator, timestamps, inputs, snapshot identifiers, expected outputs, lock state, and status `running`.
6. Freeze the snapshot for this run. Later source changes belong to the next run.

## Safety

This activity is read-only except for the Assessment Run Record and lock. It does not modify the delivery manifest, code, Charter, tickets, or deployment.

## Completion evidence

A unique run directory and record exist; input versions and snapshot boundary are reproducible; one-run-at-a-time behavior is demonstrated; and downstream activities can reference the same run ID.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

- **Assessment Run Record** (Document) - Required

## Artifacts Consumed

- **Delivery Management Assignment** (Document) - Required
- **Project Charter** (Document) - Required
- **Huginn Assessment Contract** (Document) - Required
- **Iteration Frame** (Document) - Optional
- **Iteration Goal Contract** (Document) - Optional

## Notes

No additional notes.
