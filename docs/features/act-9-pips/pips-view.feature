Feature: FOB-PIP-DETAIL-1 View PIP Details with Galdr Recommendations
  As a methodology author (Maria)
  I want to view the full detail of a PIP including Galdr's per-Change assessment
  So that I understand what decision was made and why

  # MVP simplified: Owner or Administrator finalizes after Reviewed status.
  # Public viewers (authenticated but not owner) can view PIP details but cannot finalize.
  # Anonymous guests cannot access PIP routes; playbook content browse does not include PIP list for guests (deferred).
  # MVP: banner says "owner or Administrator"; owner finalize in FOB is @mvp_gap (post-MVP).
  # For MVP the banner may read "Administrator" only until owner finalize UI ships.

  Status: 🔲 TODO
  Related: act-9-pips/pips-list.feature, act-9-pips/pips-admin-review.feature

  Background:
    Given Maria is authenticated in FOB
    And PIP-42 exists:
      | field           | value                                         |
      | id              | 42                                            |
      | title           | Add Accessibility Audit                       |
      | summary         | React playbook lacks WCAG 2.1 AA coverage     |
      | target_playbook | React Frontend Dev v1.0 (id=1)                |
      | submitted_by    | maria                                         |
      | submitted_at    | 2026-05-14T09:00:00                           |
      | status          | Reviewed                                      |
    And PIP-42 has the following Changes:
      | # | type  | entity_type | name / target             | position / rationale                          |
      | 1 | ADD   | Activity    | Accessibility Audit       | After: Component Testing (id=22)              |
      | 2 | ALTER | Activity    | Component Testing (id=22) | Add axe-core alongside existing Jest tests    |
    And Galdr has assessed PIP-42 with the following recommendations:
      | change | recommendation       | reasoning                                                                                   |
      |      1 | ACCEPT               | Consistent with Testing phase goal; no upstream conflicts detected.                         |
      |      2 | REJECT               | Proposed content removes the required Artifact link to "Test Suite", breaking dependencies. |

  # ============================================================================
  # PAGE LOAD
  # ============================================================================

  Scenario: FOB-PIP-DETAIL-01 Open PIP detail from list
    Given Maria is on FOB-PIP-LIST-1
    When she clicks [View] on PIP-42
    Then she is redirected to FOB-PIP-DETAIL-1 for PIP-42
    And the breadcrumb shows "PIPs > Add Accessibility Audit"
    And the page title shows "PIP-42: Add Accessibility Audit"

  Scenario: FOB-PIP-DETAIL-02 Header shows all PIP metadata
    Given Maria is on FOB-PIP-DETAIL-1 for PIP-42
    Then she sees:
      | field           | value                              |
      | PIP ID          | PIP-42                             |
      | Title           | Add Accessibility Audit            |
      | Target Playbook | React Frontend Dev v1.0            |
      | Submitted by    | Maria Rodriguez                    |
      | Submitted at    | 2026-05-14                         |
      | Status          | Reviewed (purple badge)            |

  Scenario: FOB-PIP-DETAIL-03 Summary section shows author rationale
    Given Maria is on FOB-PIP-DETAIL-1 for PIP-42
    Then she sees the Summary section with text "React playbook lacks WCAG 2.1 AA coverage"

  # ============================================================================
  # CHANGE LIST — GALDR RECOMMENDATIONS
  # ============================================================================

  Scenario: FOB-PIP-DETAIL-04 Change list shows all Changes with Galdr output
    Given Maria is on FOB-PIP-DETAIL-1 for PIP-42 (status=Reviewed)
    Then she sees 2 Change cards
    And Change #1 shows:
      | field          | value                                                        |
      | type_badge     | ADD                                                          |
      | entity_type    | Activity                                                     |
      | name           | Accessibility Audit                                          |
      | position       | After: Component Testing (id=22)                            |
      | galdr_verdict  | ACCEPT (green badge)                                        |
      | galdr_reason   | Consistent with Testing phase goal; no upstream conflicts.  |
    And Change #2 shows:
      | field          | value                                                        |
      | type_badge     | ALTER                                                        |
      | entity_type    | Activity                                                     |
      | target_name    | Component Testing (id=22)                                   |
      | galdr_verdict  | REJECT (red badge)                                          |
      | galdr_reason   | Proposed content removes the required Artifact link to "Test Suite", breaking dependencies. |

  Scenario: FOB-PIP-DETAIL-05 Galdr panel absent while Processing
    Given PIP-28 has status "Processing (Galdr)"
    And Galdr has not yet written recommendations for PIP-28
    When Maria opens FOB-PIP-DETAIL-1 for PIP-28
    Then she sees status banner "Galdr is reviewing your changes — check back shortly."
    And no Galdr verdict badges are shown on any Change card

  Scenario: FOB-PIP-DETAIL-06 Galdr panel absent for Draft PIPs
    Given PIP-30 has status "Draft"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-30
    Then she sees status banner "Draft — not yet submitted for review."
    And no Galdr verdict is shown on any Change card

  Scenario: FOB-PIP-DETAIL-07 Change content visible on expand
    Given Maria is on FOB-PIP-DETAIL-1 for PIP-42
    When she clicks [Expand] on Change #1
    Then she sees the full proposed content:
      """
      Ensure React components meet WCAG 2.1 AA standards.
      Install axe-core and jest-axe; add a11y tests to the component suite;
      configure automated checks in CI/CD.
      """

  # ============================================================================
  # STATUS BANNERS
  # ============================================================================

  Scenario: FOB-PIP-DETAIL-08 Status banner for Reviewed — awaiting owner or Admin
    Given PIP-42 has status "Reviewed"
    When Maria is on FOB-PIP-DETAIL-1 for PIP-42
    Then she sees the status banner "Reviewed — awaiting owner or Administrator decision."
    # MVP simplified: copy says "owner or Administrator". For MVP the banner may read
    # "Administrator" only until the owner finalize UI in FOB ships (@mvp_gap).

  Scenario: FOB-PIP-DETAIL-09 Status banner for Accepted
    Given PIP-38 has status "Accepted" and was decided on "2026-04-22"
    And PIP-38 Change #1 Admin decision is ACCEPT
    And PIP-38 Change #2 Admin decision is ACCEPT
    When Maria opens FOB-PIP-DETAIL-1 for PIP-38
    Then she sees banner "Accepted — all changes applied. React Frontend Dev is now v2.0."
    And Change #1 shows Admin verdict "ACCEPTED" (green)
    And Change #2 shows Admin verdict "ACCEPTED" (green)

  Scenario: FOB-PIP-DETAIL-10 Status banner for Partially Accepted
    Given PIP-42 is now "Accepted" with:
      | change | admin_decision |
      |      1 | ACCEPT         |
      |      2 | REJECT         |
    When Maria opens FOB-PIP-DETAIL-1 for PIP-42
    Then she sees banner "Partially accepted — 1 of 2 changes applied. React Frontend Dev is now v2.0."
    And Change #1 shows Admin verdict "ACCEPTED" (green)
    And Change #2 shows Admin verdict "REJECTED" (red)

  Scenario: FOB-PIP-DETAIL-11 Status banner for fully Rejected
    Given PIP-35 has status "Rejected" and all Changes were rejected by Admin
    When Maria opens FOB-PIP-DETAIL-1 for PIP-35
    Then she sees banner "Rejected — no changes were applied."
    And each Change card shows Admin verdict "REJECTED" (red)

  # ============================================================================
  # ACTIONS AVAILABLE TO SUBMITTER
  # ============================================================================

  Scenario: FOB-PIP-DETAIL-12 Draft PIP shows Edit and Cancel buttons
    Given PIP-30 has status "Draft"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-30
    Then she sees [Edit PIP] button
    And she sees [Cancel] button
    And she sees [Submit for Review] button

  Scenario: FOB-PIP-DETAIL-13 Submitted PIP shows Cancel button
    Given PIP-28 has status "Submitted"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-28
    Then she sees [Cancel PIP] button
    And she does NOT see [Edit PIP]
    And she does NOT see [Submit for Review]

  Scenario: FOB-PIP-DETAIL-14 Reviewed / Accepted / Rejected PIPs are read-only for submitter
    Given PIP-42 has status "Reviewed"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-42
    Then she sees no action buttons (view-only)
    And the status banner explains current state

  Scenario: FOB-PIP-DETAIL-15 Discard Draft PIP from detail page
    Given PIP-30 has status "Draft"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-30 and clicks [Cancel]
    Then a confirmation modal appears: "Cancel PIP-30 permanently?"
    When she clicks [Confirm]
    Then PIP-30 is deleted
    And she is redirected to FOB-PIP-LIST-1
    And PIP-30 no longer appears in the list

  Scenario: FOB-PIP-DETAIL-16 Submit for Review from detail page
    Given PIP-30 has status "Draft" and has 3 Changes
    When Maria opens FOB-PIP-DETAIL-1 for PIP-30 and clicks [Submit for Review]
    Then PIP-30 status changes to "Submitted"
    Then within seconds the status transitions to "Processing (Galdr)"
    And a notification appears: "PIP 'Add Figma Integration' submitted — Galdr is reviewing your changes."
    And the [Submit for Review] and [Edit PIP] buttons disappear
    And the [Cancel PIP] button appears

  # ============================================================================
  # EMAIL NOTIFICATION CONTENT
  # ============================================================================

  Scenario: FOB-PIP-DETAIL-17 Maria receives email when Admin decides — all accepted
    Given PIP-38 is decided by Admin with all Changes ACCEPTED
    Then Maria receives an email:
      | field   | value                                                          |
      | subject | Your PIP "State Management Patterns" — Accepted ✓              |
      | body_contains | Change 1: ADD Activity "Redux Setup" → Accepted      |
      | body_contains | Reasoning: Consistent with State Management workflow goal. |
      | body_contains | Change 2: ALTER Activity "Component Testing" → Accepted    |
      | body_contains | Overall: Accepted. Version 2.0 published with your changes. |

  Scenario: FOB-PIP-DETAIL-18 Maria receives email when Admin decides — partially accepted
    Given PIP-42 is decided by Admin with Change #1 ACCEPT and Change #2 REJECT
    Then Maria receives an email with subject "Your PIP "Add Accessibility Audit" — Partially Accepted"
    And the email body contains:
      | line                                                                              |
      | Change 1: ADD Activity "Accessibility Audit" → Accepted                          |
      | Reasoning: Consistent with Testing phase goal; no upstream conflicts detected.   |
      | Change 2: ALTER Activity "Component Testing" → Rejected                          |
      | Reasoning: Proposed content removes the required Artifact link to "Test Suite".  |
      | Overall: Partially accepted. Version 2.0 published with Change 1 applied.        |

  Scenario: FOB-PIP-DETAIL-19 Maria receives email when Admin decides — fully rejected
    Given PIP-35 is decided by Admin with all Changes REJECTED
    Then Maria receives an email with subject "Your PIP "Drop Legacy IE Support" — Rejected ✗"
    And the email body contains "Overall: Rejected. No changes were applied."

  # ============================================================================
  # WITHDRAW (EDIT & RESUBMIT)
  # ============================================================================

  Scenario: FOB-PIP-DETAIL-20 Submitted PIP shows Withdraw button
    Given PIP-28 has status "Submitted"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-28
    Then she sees [Withdraw] button
    And she does NOT see [Edit PIP]
    And she does NOT see [Submit for Review]
    And the status banner reads "Submitted — queued for Galdr review."

  Scenario: FOB-PIP-DETAIL-21 Processing (Galdr) PIP shows Withdraw button
    Given PIP-27 has status "Processing (Galdr)"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-27
    Then she sees [Withdraw] button
    And the status banner reads "Galdr is reviewing your changes — check back shortly."

  Scenario: FOB-PIP-DETAIL-22 Withdraw shows confirmation modal with clear warning
    Given PIP-28 has status "Submitted"
    And Maria is on FOB-PIP-DETAIL-1 for PIP-28
    When she clicks [Withdraw]
    Then a confirmation modal appears:
      """
      Withdraw PIP-28?
      It will return to Draft and any in-progress Galdr review will be discarded.
      """
    And the modal has [Confirm] and [Cancel] buttons
    When she clicks [Cancel]
    Then the modal closes and PIP-28 status is still "Submitted"

  Scenario: FOB-PIP-DETAIL-23 Confirming Withdraw on Submitted PIP reverts status to Draft
    Given PIP-28 has status "Submitted"
    And Maria is on FOB-PIP-DETAIL-1 for PIP-28
    When she clicks [Withdraw] and confirms
    Then PIP-28 status becomes "Draft"
    And she sees [Edit PIP] button
    And she sees [Submit for Review] button
    And she sees [Discard] button
    And no Galdr verdict badges are shown on any Change card
    And the status banner reads "Draft — not yet submitted."

  Scenario: FOB-PIP-DETAIL-24 Confirming Withdraw on Processing PIP aborts Galdr and clears recommendations
    Given PIP-27 has status "Processing (Galdr)"
    And Galdr has partially written recommendations for PIP-27
    When Maria opens FOB-PIP-DETAIL-1 for PIP-27 and clicks [Withdraw] and confirms
    Then PIP-27 status becomes "Draft"
    And all Galdr recommendations on PIP-27 Changes are cleared
    And no galdr_verdict badges appear on any Change card

  Scenario: FOB-PIP-DETAIL-25 Withdrawn Draft can be edited and resubmitted
    Given PIP-27 was withdrawn and now has status "Draft" with 1 existing Change
    When Maria opens FOB-PIP-DETAIL-1 for PIP-27 and clicks [Edit PIP]
    Then she can add, modify, or remove Changes
    When she adds Change #2 (ALTER Activity "Component Testing")
    And clicks [Submit for Review]
    Then PIP-27 status becomes "Submitted"
    And within seconds transitions to "Processing (Galdr)"
    And a notification appears: "PIP 'Rename Discovery Activity' submitted — Galdr is reviewing your changes."

  Scenario: FOB-PIP-DETAIL-26 Reviewed PIP does not show Withdraw button
    Given PIP-42 has status "Reviewed"
    When Maria opens FOB-PIP-DETAIL-1 for PIP-42
    Then she does NOT see [Withdraw]
    And she sees no action buttons (view-only)
