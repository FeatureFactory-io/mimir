# Cedar contribution discovery job

This is a fictional replay case, not a record of customer interviews. It defines
the progress the feature must support before we choose its screens or models.

## Elena Svensson and the triggering situation

Elena leads Meridian Methods' competency center. Noor's Cedar bank onboarding
RFP needs somebody who can explain keyboard navigation, understandable form
errors and recovery. Elena has until Tuesday noon to return a name, a reason
and a public example of that person's work. She knows the visible people but
cannot defend which contribution history fits this problem.

Her first question is: **Who should I talk to, and why that person?**

## JTD CEDAR 01

**When** a bid requires a contributor in an unfamiliar area, **I want to** find
people by playbook category, inspect their public contribution evidence and
obtain an appropriate contact handoff, **so I can** give the bid manager a
defensible candidate for a discussion before the response deadline.

Successful progress is a nomination note containing a person, a relevant public
released playbook, a reason connected to the brief, and the next contact action.
A rank or score alone is insufficient. Availability, willingness and project
suitability still require a conversation.

**Proposed UAT criterion:** from an authenticated starting session, complete the
nomination in five minutes without a developer explaining the route. Measure
the actual attempt; a stopwatch pass is not yet an observed fact.

## Supporting jobs

| Person | Situation and job | Observable completion |
| --- | --- | --- |
| Maria Rodriguez, UX contributor | Understand how published work and accepted improvements are represented to others | Own profile source breakdown reconciles, full summary expands, public profile reveals no private data |
| Bob, an unregistered visitor | Evaluate whether public contribution evidence is useful before registering | Read list and public profile; contact control explains that sign-in is required |
| Mike Chen, playbook author | Receive consistent credit when another signed-in person uses public content | One eligible consumption awards five points to consumer and author; guests and self-use do not award points |
| Administrator | Accept an eligible proposal with the normal decision process | Only accepted changes earn their specified points; the decision notification is captured locally in this replay |

## Why these data change the design

Sofia Reed leads Design with 15,400 Karma. Her published work concerns service
blueprints and design operations. Maria has 8,200 total Karma and an Accessibility
Audit Playbook with keyboard-focus and form-feedback activities. Sofia remains
a credible contributor; Maria's examples are closer to Noor's brief. Elena must
be able to inspect evidence rather than mistake first place for a recommendation.

Maria's Design subtotal is 7,200 while Priya Nair has 7,600. Maria's additional
1,000 Development points put her total above Priya's. Sorting a Design view by
its subtotal would reverse these two people and implement a different rule.

Theo Martin is the sixth eligible Design contributor and tests the top-five
boundary. Mike's 12,450 belongs to Development and tests category isolation.
Nora Berg has zero points and tests eligibility. Other has no contributors and
tests an honest empty state. Bob tests guest access. Long summaries, a missing
avatar, a non-expert public profile and a missing username test actual variants.

The complete proposed domain dataset is CEDAR-RFP-01. It is a data contract,
not yet an importable Django fixture. The adapter will be implemented after
PIN GO, with separate test DBs and replay environment ownership checks.

## Capability hypothesis

| Candidate approach | Discover | Inspect evidence | Contact handoff | Decision |
| --- | --- | --- | --- | --- |
| Ask colleagues | Depends on who replies | Depends on their explanation | Usually available | Useful fallback; hard to repeat or verify |
| Browse playbook authors | Manual across playbooks | Yes | Fragmented | Evidence exists but category discovery is slow |
| Enrich private profiles | Limited to known people | Partial | Account dependent | Does not provide public discovery |
| Category discovery plus public evidence | Yes | Yes | Authenticated handoff | Supports the complete Cedar job |

Call the discover-and-inspect capability **Experts**. Present top contributors
by their primary playbook category. Use contribution history as a starting point
for discovery, then let Elena inspect public evidence and choose whom to contact.
The display must not claim that rank certifies expertise, availability or fit.

## Scope boundaries and completion evidence

The brief and nomination are external case props. This feature adds no RFP,
shortlist, messaging, calendar, hiring or availability workflow inside Mimir.
For signed-in Elena, Reach out supplies Maria's mailto contact. In the recording
we inspect that handoff; we do not send a real email to anyone.

The final case note should read:

> Candidate: Maria Rodriguez. Evidence: Accessibility Audit Playbook v1.0 and
> published keyboard-navigation and form-feedback contributions. Reason: these
> examples address the accessibility review requested in the Cedar brief. Next
> action: request a discussion at maria.rodriguez@example.com. Availability is
> not yet confirmed.

## Quality risks to make observable

1. Wrong behavior: subtotal sorting changes Maria's position; guest contact or
   scoring rules can be wrong even when a page looks plausible.
2. Wrong look: the evidence or contact action can be hard to discover or read,
   preventing Elena from completing the job.
3. Design drift: a new font, color or component treatment can disconnect Experts
   from the existing Mimir design system across screens and viewport sizes.

Next: extend the journey, map each state to the existing IA recipe, specify
concrete data and outcomes, extend UAT using DO/SEE/RECORD/IF DIFFER, then build
ESM mockups from the actual shared Django shell and design tokens.
