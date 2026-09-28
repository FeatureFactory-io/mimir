# Activity: Set Up Huginn

**Activity ID**: 550
**Order**: 6
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 565 (Complete Inception and Elaboration)
Successor: Activity 551 (Run First Iteration, Ship Increment)

## Description

Set Up Huginn

## Guidance

## Objective

Configure Huginn to execute the AIN assessment contract manually and, when appropriate, on a schedule. Huginn observes and reports; it does not redefine Charter variables or bypass delivery gates.

## Required inputs

- Approved Charter v0 at `docs/project/CHARTER.md`.
- A runnable repository with its delivery/test commands.
- Completed Inception and Elaboration readiness evidence.
- A selected GH or Jira ticket adapter and credentials supplied through the project's approved secret mechanism.

## Procedure

1. Inspect existing Huginn configuration and repository automation before creating anything.
2. Create `docs/project/HUGINN_ASSESSMENT_CONTRACT.md` containing:
   - repository and environment identity;
   - manual trigger and schedule;
   - exact source/query/command for every Charter variable;
   - assessment snapshot boundary and freshness limit;
   - ticket system, project/repository, labels/types, and stable concern key;
   - expected-artifact paths and staleness checks;
   - notification and escalation destinations;
   - retry, timeout, and overlapping-run policy.
3. Configure one AIN run at a time per project. A second trigger must reuse or wait for the active run, not race it.
4. Run AIN once manually against known data.
5. Verify the persisted Assessment Run Record, ticket action, throughput result, coverage result, and final report.
6. Enable scheduling only after the manual run passes.

## Failure handling

If a source, credential, query, or ticket adapter is missing, record the exact blocker and stop. Never substitute invented data or mark an unmeasurable variable Green.

## Completion evidence

The contract is committed, a manual run has a stable run ID and complete report, all side effects are idempotent, and the next scheduled time is visible when scheduling is enabled.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

- **Huginn Assessment Contract** (Document) - Required

## Artifacts Consumed

- **Delivery Management Assignment** (Document) - Required
- **Project Charter** (Document) - Required
- **Elaboration Readiness Record** (Document) - Required

## Notes

No additional notes.
