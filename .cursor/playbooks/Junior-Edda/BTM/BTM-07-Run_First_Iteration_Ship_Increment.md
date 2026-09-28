# Activity: Run First Iteration, Ship Increment

**Activity ID**: 551
**Order**: 7
**Phase**: Construction
**Dependencies**: Predecessor: Activity 550 (Set Up Huginn)
Successor: Activity 552 (Hold Retrospective, Update Charter)

## Description

Run First Iteration, Ship Increment

## Guidance

## Objective

Run the first complete delivery cycle with the team and ship one bounded, accepted increment while the Charter assumptions are still provisional.

## Preconditions

- Charter v0 is approved.
- ESM, DTA, DSP, required estimation/infrastructure/CI-CD work, BSP, and applicable test-framework setup are complete.
- Huginn can run AIN manually even if scheduling is not yet enabled.
- One candidate goal can fit the cadence selected by RIN.

## Procedure

1. Invoke Workflow **Run the Iteration (RIN)**; do not duplicate its activities here.
2. Keep the Delivery Manager and team together for this first pass. Record every place where the Charter, tooling, ownership, or activity guidance is insufficient.
3. When RIN starts MIN, launch or schedule **Assess the Iteration (AIN)** as the independent supervisory stream. If the ADE supports subagents/background tasks, keep AIN separate from the MIN execution context.
4. Preserve every PIN/MIN human gate. Parallel execution does not authorize merging, releasing, purchasing, or changing scope.
5. Ship only when the selected increment passes its declared acceptance, regression, and release checks.

## Completion evidence

Record the iteration goal, manifest/milestone, release or deployment identifier, acceptance result, latest AIN report, unresolved tickets, and observed process defects. A plan without a shipped and verified increment does not complete this activity.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **Elaboration Readiness Record** (Document) - Required
- **Huginn Assessment Contract** (Document) - Required

## Notes

No additional notes.
