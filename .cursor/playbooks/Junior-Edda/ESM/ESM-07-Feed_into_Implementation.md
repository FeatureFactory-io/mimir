# Activity: Feed into Implementation

**Activity ID**: 41
**Order**: 7
**Phase**: Inception
**Dependencies**: Predecessor: Activity 40 (Create Mockups)

## Description

Feed into Implementation

## Guidance

# Feed into Feature Implementation Workflow

## Objective

Transition from UX design to full backend implementation.

## Process

### 1. Handoff Checklist

Ensure all UX artifacts are complete before implementation:

**Activity 1 → Activity 2**:
- [ ] Screen ID convention understood
- [ ] Traceability requirements clear
- [ ] Important guidelines reviewed

**Activity 2 → Activity 3**:
- [ ] User journey documented
- [ ] All Acts defined with personas
- [ ] Screen IDs assigned to all screens

**Activity 3 → Activity 4**:
- [ ] IA guidelines documented
- [ ] Design system tokens defined
- [ ] Navigation structure clear

**Activity 4 → Activity 5**:
- [ ] Domain model diagram complete
- [ ] MVP flow diagram shows all screens
- [ ] Screen states documented
- [ ] Flow validated visually (human eye check)

**Activity 5 → Activity 6**:
- [ ] All CRUDLF feature files written
- [ ] Scenarios follow BDD best practices
- [ ] Navbar integration scenarios added
- [ ] Error/edge cases covered

**Activity 6 → Activity 7**:
- [ ] All mockup templates created
- [ ] Mock views functional
- [ ] All UI states represented
- [ ] Accessibility attributes present
- [ ] `data-testid` attributes added
- [ ] Design system compliance verified

**Activity 7 — UX complete**:
- [ ] All UX artifacts complete (Activities 1-6)
- [ ] Feature files ready for implementation
- [ ] Mockups ready for conversion to real views
- [ ] Screen IDs documented across all artifacts

### 2. Traceability Verification

Verify Screen ID appears in all 5 artifacts:
1. ✅ User Journey (section header)
2. ✅ Screen Flow Diagram (box label)
3. ✅ Feature File (feature title)
4. ✅ Template (HTML comment + hidden div)
5. ✅ Tests (test names + docstrings)

**Grep Test**: `grep -r "FOB-{ENTITY}-{OPERATION}-{VERSION}" .`

## Deliverables

- ✅ All UX artifacts complete (Activities 1-6)
- ✅ Feature files ready for implementation
- ✅ Mockups ready for implementation
- ✅ **Screen ID traceability complete**
- ✅ Handoff checklist verified

## Next Steps: Remaining Elaboration before Construction

ESM is the first Inception workflow. Three more workflows must complete before building starts:

| Gate | Artifact | Workflow if missing |
|------|----------|---------------------|
| DTA | `docs/architecture/SAO.md` | DTA — Define Architecture |
| DSP | `CLAUDE.md` | DSP — Deploy Software Process |
| BSP | `Makefile` + `requirements.txt` | BSP — Bootstrap Project |

Run DTA next. DSP follows DTA (needs SAO.md). BSP follows DSP. When all four gates pass, see BSP-08 for the Construction Handoff and mode selection.

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
