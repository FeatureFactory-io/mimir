# Activity: Measure Delivery Throughput

**Activity ID**: 563
**Order**: 4
**Phase**: Construction
**Dependencies**: Predecessor: Activity 560 (Open an Assessment Run)
Successor: Activity 562 (Reconcile Risk and Problem Tickets)

## Description

Measure Delivery Throughput

## Guidance

## Objective

Measure accepted delivery flow from the same assessment snapshot independently of variable assessment and ticket mutation.

## Procedure

1. Use the iteration ID, repository revision, and source cursors from `RUN.md`.
2. Read the authoritative delivery records declared in the Huginn contract (for example accepted scenario issues, merged changes, releases, and acceptance checks).
3. Count completed accepted items in the declared cadence/window. Also record cycle time and work-in-progress when the source supports them.
4. Story points are optional and must not replace item throughput unless the Charter explicitly defines their source and use.
5. Exclude reopened, rejected, duplicate, or unaccepted work and record the exclusion reason.
6. Write `THROUGHPUT.json` with window, sources/queries, counts, item IDs, exclusions, cycle-time summary, WIP, freshness, and errors.

## Completion evidence

The result is reproducible from named records, uses the run snapshot and cadence window, distinguishes accepted work from activity volume, and expresses missing/stale data as Unknown rather than zero.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

- **Delivery Throughput Snapshot** (Document) - Required

## Artifacts Consumed

- **Assessment Run Record** (Document) - Required

## Notes

No additional notes.
