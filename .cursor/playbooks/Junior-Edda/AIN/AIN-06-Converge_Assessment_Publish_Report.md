# Activity: Converge Assessment & Publish Report

**Activity ID**: 566
**Order**: 6
**Phase**: Construction
**Dependencies**: Predecessor: Activity 562 (Reconcile Risk and Problem Tickets)

## Description

Converge Assessment & Publish Report

## Guidance

## Objective

Join all assessment branches, publish one complete supervisory verdict, and release the project assessment lock.

## Required inputs

For the same run ID: Assessment Run Record, Variable Assessment Evidence, Ticket Action Record, Delivery Throughput Snapshot, and Required-Artifact Coverage Report.

## Procedure

1. Verify every required input exists, validates, and uses the same run ID, Charter version, iteration ID, and snapshot boundary.
2. If any branch is missing, stale, schema-invalid, or has an unresolved side-effect error, mark the run `incomplete`; do not publish a success verdict or release an ambiguous partial report.
3. Create `ITERATION_ASSESSMENT.md` containing:
   - run/snapshot identity and input versions;
   - executive verdict: `Green | Yellow | Orange | Red | Unknown`;
   - per-variable prior/current band, evidence, ticket action, owner, and gating policy;
   - throughput and cycle-time findings;
   - artifact-coverage findings;
   - active `observe | pause_new_work | block_release` signals;
   - required next actions with owner and due/decision point;
   - errors, Unknowns, and confidence/provenance limitations.
4. Derive the overall verdict from declared Charter policy. Never average away a Red, Unknown, or gating signal.
5. Update `RUN.md` to `complete` with output checksums/links and end time; release the lock.
6. Notify the Delivery Manager and the RIN/MIN execution context through the destinations in the Huginn contract.

## Completion evidence

The report is reproducible, internally consistent, complete for all branches, explicit about Unknowns and gates, linked to stable tickets, and the run record is complete with the lock released.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

- **Iteration Assessment Report** (Document) - Required

## Artifacts Consumed

- **Project Charter** (Document) - Required
- **Assessment Run Record** (Document) - Required
- **Variable Assessment Evidence** (Document) - Required
- **Project-Management Ticket** (Other) - Optional
- **Ticket Action Record** (Document) - Required
- **Delivery Throughput Snapshot** (Document) - Required
- **Required-Artifact Coverage Report** (Document) - Required

## Notes

No additional notes.
