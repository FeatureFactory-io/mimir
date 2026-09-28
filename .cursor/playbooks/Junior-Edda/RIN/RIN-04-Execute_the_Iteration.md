# Activity: Execute the Iteration

**Activity ID**: 556
**Order**: 4
**Phase**: Construction
**Dependencies**: Predecessor: Activity 555 (Plan the Iteration)
Successor: Activity 557 (Hold the Iteration Retrospective)

## Description

Execute the Iteration

## Guidance

## Objective

Execute the approved manifest through **Manage the Iteration (MIN)** while **Assess the Iteration (AIN)** observes independently.

## Procedure

1. Invoke MIN with the accepted PIN output; do not re-plan it inside this activity.
2. When MIN begins, trigger AIN as a separate/background stream against the same project and iteration ID. If the ADE supports subagents or parallel tasks, isolate AIN from delivery-worker contexts. Otherwise schedule AIN checkpoints without blocking independent delivery work.
3. MIN owns delivery dispatch, checkpoints, drift, integration, and its human gates. AIN owns measurement, ticket lifecycle, throughput, coverage, and its final assessment report.
4. Apply the latest assessment signals:
   - `observe`: record and continue.
   - `pause_new_work`: finish safe in-flight checkpoints but dispatch no new work until resolved/waived.
   - `block_release`: continue safe work but do not release until resolved/waived.
5. Never let AIN edit the MIN manifest or production code. Never let MIN mark an assessment concern Green without AIN evidence.
6. Preserve all required human approvals for scope, merge, release, purchase, or external side effects.

## Completion evidence

MIN reaches an explicit complete/escalated state; every checkpoint result and drift decision is recorded; the latest AIN run is complete or explicitly pending; gating signals were enforced; and any shipped increment has verified acceptance and release evidence.

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

- **Iteration Frame** (Document) - Required
- **Iteration Goal Contract** (Document) - Required
- **Project-Management Ticket** (Other) - Optional

## Notes

No additional notes.
