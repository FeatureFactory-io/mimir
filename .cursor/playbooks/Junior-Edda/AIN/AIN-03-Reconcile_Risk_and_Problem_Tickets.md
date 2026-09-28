# Activity: Reconcile Risk and Problem Tickets

**Activity ID**: 562
**Order**: 3
**Phase**: Construction
**Dependencies**: Predecessor: Activity 561 (Assess Charter Variables)
Successor: Activity 566 (Converge Assessment & Publish Report)

## Description

Reconcile Risk and Problem Tickets

## Guidance

## Objective

Apply the measured variable results to a stable, idempotent Risk/Problem ticket lifecycle.

## Procedure

1. Load `VARIABLE_RESULTS.json` and the configured GH/Jira adapter.
2. For each variable derive `concern_key = <project_id>:<variable_id>`.
3. Fan out read-only ticket lookup if useful, then serialize all creates/updates/closes per `concern_key`. Never let two workers mutate the same concern.
4. Apply this state machine:
   - Green with no open concern: no action.
   - Yellow/Orange: create or update one **Risk** ticket.
   - Red: create or update one **Problem** ticket; convert the same concern when the adapter supports type change, otherwise link/close the old representation atomically.
   - Unknown: never close or green a concern. Create/update the same concern as a measurement-health Risk unless the Charter declares a stricter treatment.
   - Return to Green: resolve the open concern only with fresh Green evidence.
5. On Yellow↔Orange, band changes, new evidence, changed severity, or gating-policy changes, update the existing ticket even when its type does not change.
6. Use `<run_id>:<variable_id>` as the idempotency key. Retry must yield the same ticket and action record.
7. Emit `TICKET_ACTIONS.json` with prior/new state, action, ticket ID/URL, evidence, gating policy, and errors.

## Failure handling

A ticket-adapter failure does not erase the measurement. Mark the action failed, keep the run incomplete, and retry idempotently. Never create a substitute duplicate.

## Completion evidence

Every non-Green/Unknown variable has exactly one stable concern; lifecycle changes reflect evidence; gating signals are explicit; and a repeated run/retry creates no duplicate ticket.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

- **Band → Ticket Type Mapping** (`band-ticket-type-mapping`)
- **One Ticket Per Concern** (`one-ticket-per-concern`)
- **Ticket Lifecycle Transitions** (`ticket-lifecycle-transitions`)

## Artifacts Produced

- **Project-Management Ticket** (Other) - Optional
- **Ticket Action Record** (Document) - Required

## Artifacts Consumed

- **Assessment Run Record** (Document) - Required
- **Variable Assessment Evidence** (Document) - Required

## Notes

No additional notes.
