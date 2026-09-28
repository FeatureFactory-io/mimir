# Activity: Assess Charter Variables

**Activity ID**: 561
**Order**: 2
**Phase**: Construction
**Dependencies**: Predecessor: Activity 560 (Open an Assessment Run)
Successor: Activity 562 (Reconcile Risk and Problem Tickets)

## Description

Assess Charter Variables

## Guidance

## Objective

Measure every Charter variable from the run snapshot and produce evidence; do not create or update tickets here.

## Procedure

1. Read the variable contracts from the Charter version recorded in `RUN.md`.
2. If the ADE supports parallel workers, fan out one bounded worker per variable (or per non-overlapping source batch). Every worker is read-only and writes only `variables/<variable_id>.json`; no two workers share an output file or ticket key.
3. For each variable execute the exact declared query/command and record:
   - `variable_id`, definition, unit, source, query/command, window;
   - raw result or bounded evidence reference;
   - observed timestamp and source timestamp;
   - freshness and validation result;
   - current value;
   - prior and current band: `Green | Yellow | Orange | Red | Unknown`;
   - threshold calculation and owner;
   - measurement error, if any.
4. Missing, stale, inaccessible, malformed, or non-reproducible evidence is `Unknown`, never Green. Apply the Charter's declared Unknown policy without inventing a value.
5. After all workers finish, validate schema and coverage and produce `VARIABLE_RESULTS.json` sorted by stable variable ID.

## Completion evidence

There is exactly one valid result per Charter variable; all results use the same run ID/snapshot; failures are explicit Unknowns; raw provenance is retained; and no ticket or delivery state was mutated.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

- **Charter Is Source of Truth for Variables** (`charter-is-source-of-truth-for-variables`)
- **Variable Band Scale Flexibility** (`variable-band-scale-flexibility`)

## Artifacts Produced

- **Variable Assessment Evidence** (Document) - Required

## Artifacts Consumed

- **Project Charter** (Document) - Required
- **Assessment Run Record** (Document) - Required

## Notes

No additional notes.
