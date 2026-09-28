# Activity: Hold Retrospective, Update Charter

**Activity ID**: 552
**Order**: 8
**Phase**: Construction
**Dependencies**: Predecessor: Activity 551 (Run First Iteration, Ship Increment)

## Description

Hold Retrospective, Update Charter

## Guidance

## Objective

Close the first shipped iteration, test the assumptions in Charter v0 against observed evidence, and publish an approved Charter v1.

## Required inputs

- `docs/project/CHARTER.md` at v0.
- The first iteration goal, manifest, release evidence, and Definition-of-Done result.
- The latest Iteration Assessment Report and all open Risk/Problem tickets.
- Any Iteration Improvement Proposals (IIPs).
- Participants from the Charter Team Roster.

## Procedure

1. Create `docs/project/retros/BOOTSTRAP_RETRO.md`.
2. Record what was expected, what happened, evidence, and consequences. Separate facts from opinions.
3. Review every Charter section:
   - goals and success measures;
   - roster, authority, and ownership;
   - team maturity classification and its evidence;
   - tracked-variable measurement contracts and thresholds;
   - required-artifact coverage;
   - meeting cadence;
   - aspirational roadmap.
4. Review each IIP. Record `accepted`, `rejected`, or `deferred`, with owner and reason.
5. Update `docs/project/CHARTER.md` to v1. Add a dated change log; never silently overwrite v0 assumptions.
6. Obtain explicit sponsor/Delivery Manager approval.

## Completion evidence

- Bootstrap retrospective exists and cites iteration evidence.
- Charter says `Version: 1`, contains the dated diff, and has no undefined variable source, threshold, owner, or gating policy.
- Every IIP and open Risk/Problem ticket has a disposition or named owner.
- Approval is recorded. Do not declare Bootstrap complete without it.

## Agent

**Name**: Delivery Manager (DM)
**Description**: Single merged PM/DM role. Staffed at Kickoff. Owns the Charter, is the recipient of all Risk/Problem tickets raised by Assess the Iteration, presides over cadence meetings, and determines iteration cadence/length.

## Skill

None

## Rules

None

## Artifacts Produced

- **Bootstrap Retrospective & Charter Update** (Document) - Required

## Artifacts Consumed

- **Project Charter** (Document) - Required
- **Iteration Retrospective** (Document) - Required
- **Iteration Improvement Proposal (IIP)** (Document) - Required
- **Iteration Closeout** (Document) - Required
- **Iteration Assessment Report** (Document) - Required

## Notes

No additional notes.
