Feature: FOB-MCP-PIPS-1 AI Assistant Interacts with PIPs via MCP
  As an AI assistant (Cascade)
  I want to list, create, edit, submit, cancel, revert, and view PIPs via MCP tools
  So that I can help users propose, refine (after Galdr feedback), and track structured improvements to Released playbooks

  Status: 🔲 TODO
  Related: act-9-pips/
  Architecture: FastMCP wraps REST API endpoints at BASE_URL; authenticated with TOKEN for "maria"

  Background:
    Given FastMCP is running with BASE_URL "http://localhost:8000" and TOKEN for user "maria"
    And the following playbooks exist:
      | id | name               | status   | version |
      |  1 | React Frontend Dev | released |     1.0 |
      |  2 | UX Research        | released |     2.1 |
      |  3 | My Draft           | draft    |     0.3 |
    And playbook id=1 has:
      | entity   | id | name                    | workflow_id |
      | Workflow | 10 | Component Development   | —           |
      | Workflow | 11 | Testing & Documentation | —           |
      | Activity | 20 | Setup Project           |          10 |
      | Activity | 22 | Component Testing       |          11 |
      | Activity | 23 | Write Documentation     |          11 |
    And the following PIPs exist for user "maria":
      | id | title                     | playbook_id | status    |
      | 42 | Add Accessibility Audit   |           1 | Draft     |
      | 38 | State Management Patterns |           1 | Submitted |
      | 35 | Drop Legacy IE Support    |           1 | Reviewed  |
      | 30 | Add Figma Integration     |           2 | Accepted  |
  # ============================================================================
  # list_pips
  # ============================================================================

  Scenario: MCP-PIP-01 list_pips returns all PIPs for current user
    Given user "maria" has 4 PIPs in the system
    When Cascade calls MCP tool "list_pips" with:
      | (no parameters) |  |
    Then MCP returns a list of 4 PIPs
    And each entry contains: id, title, target_playbook_id, target_playbook_name, status, changes_count, submitted_at, last_updated_at
    And the list is ordered by last_updated_at descending

  Scenario: MCP-PIP-02 list_pips filters by status=Draft
    When Cascade calls MCP tool "list_pips" with:
      | status | Draft |
    Then MCP returns 1 PIP: PIP-42 "Add Accessibility Audit"
    And PIPs in status Submitted, Reviewed, Accepted are excluded

  Scenario: MCP-PIP-03 list_pips filters by status=Reviewed
    When Cascade calls MCP tool "list_pips" with:
      | status | Reviewed |
    Then MCP returns 1 PIP: PIP-35 "Drop Legacy IE Support"

  Scenario: MCP-PIP-04 list_pips filters by playbook_id
    When Cascade calls MCP tool "list_pips" with:
      | playbook_id | 1 |
    Then MCP returns 3 PIPs (id=42, 38, 35) targeting playbook id=1
    And PIP-30 (targeting playbook id=2) is excluded

  Scenario: MCP-PIP-05 list_pips resets status_changed_since_last_view
    Given PIP-35 has "status_changed_since_last_view" = True for maria
    When Cascade calls MCP tool "list_pips"
    Then MCP returns PIP-35 in the list
    And PIP-35 "status_changed_since_last_view" is now False
    And the count pill for the PIPs nav item will show 0 on next page load

  Scenario: MCP-PIP-06 list_pips returns empty list when no PIPs exist
    Given user "alex" has no PIPs
    When Cascade calls MCP tool "list_pips" with user context "alex"
    Then MCP returns an empty list []
    And no error is raised

  Scenario: MCP-PIP-07 list_pips does not return other users' PIPs
    Given user "alex" also has PIP-99 for playbook id=1
    When Cascade calls MCP tool "list_pips" with user context "maria"
    Then MCP returns only PIPs owned by "maria" (not PIP-99)
  # ============================================================================
  # create_pip
  # ============================================================================

  Scenario: MCP-PIP-08 create_pip creates a draft PIP targeting a released playbook
    When Cascade calls MCP tool "create_pip" with:
      | playbook_id |                                                 1 |
      | title       | Add Accessibility Audit                           |
      | summary     | Playbook lacks WCAG 2.1 AA coverage; this adds it |
    Then MCP returns success with:
      | id          | (new int)               |
      | title       | Add Accessibility Audit |
      | status      | Draft                   |
      | changes     | []                      |
      | playbook_id |                       1 |
    And a new PIP record is persisted with status "Draft" and submitted_by "maria"

  Scenario: MCP-PIP-09 create_pip on a Draft playbook raises error
    When Cascade calls MCP tool "create_pip" with:
      | playbook_id |               3 |
      | title       | Some suggestion |
    Then MCP returns error "PermissionError: PIPs can only be submitted against Released playbooks. Playbook id=3 is Draft."

  Scenario: MCP-PIP-10 create_pip with empty title raises error
    When Cascade calls MCP tool "create_pip" with:
      | playbook_id | 1 |
      | title       |   |
    Then MCP returns error "ValueError: PIP title cannot be empty"

  Scenario: MCP-PIP-11 create_pip for playbook owned by another user raises error
    Given playbook id=5 is owned by user "alice" and is released
    When Cascade calls MCP tool "create_pip" with user context "maria":
      | playbook_id |                   5 |
      | title       | My suggested change |
    Then MCP returns error "PermissionError: Playbook 5 not found or not accessible"
  # ============================================================================
  # add_change (add a Change to an existing draft PIP)
  # ============================================================================

  Scenario: MCP-PIP-12 add_change ADD Activity — append at end of workflow
    Given draft PIP-42 exists with 0 Changes
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |                                            42 |
      | change_type | ADD                                           |
      | entity_type | Activity                                      |
      | name        | Accessibility Audit                           |
      | parent_id   |                                            11 |
      | position    | append                                        |
      | content     | Ensure WCAG 2.1 AA compliance using axe-core. |
    Then MCP returns success with:
      | change_id   | (new int)           |
      | change_type | ADD                 |
      | entity_type | Activity            |
      | name        | Accessibility Audit |
      | parent_id   |                  11 |
      | position    | append              |
    And PIP-42 now has 1 Change

  Scenario: MCP-PIP-13 add_change ADD Activity — insert after sibling
    Given draft PIP-42 exists with 0 Changes
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |                                 42 |
      | change_type | ADD                                |
      | entity_type | Activity                           |
      | name        | Accessibility Audit                |
      | after_id    |                                 22 |
      | content     | WCAG 2.1 AA checks using axe-core. |
    Then MCP returns success with position "after:22"
    And PIP-42 has 1 Change with after_id=22

  Scenario: MCP-PIP-14 add_change ALTER existing Activity
    Given draft PIP-42 exists with 0 Changes
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |                                                             42 |
      | change_type | ALTER                                                          |
      | entity_type | Activity                                                       |
      | target_id   |                                                             22 |
      | content     | Add axe-core alongside Jest; fail build on any a11y violation. |
    Then MCP returns success with:
      | change_type | ALTER |
      | target_id   |    22 |
    And PIP-42 has 1 Change

  Scenario: MCP-PIP-15 add_change DROP Activity with rationale
    Given draft PIP-42 exists with 0 Changes
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |                                                                 42 |
      | change_type | DROP                                                               |
      | entity_type | Activity                                                           |
      | target_id   |                                                                 23 |
      | rationale   | Documentation is now auto-generated from code comments; redundant. |
    Then MCP returns success with change_type "DROP" and target_id=23
    And PIP-42 has 1 Change

  Scenario: MCP-PIP-16 add_change to non-Draft PIP raises error
    Given PIP-38 has status "Submitted"
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |           38 |
      | change_type | ADD          |
      | entity_type | Activity     |
      | name        | New Activity |
    Then MCP returns error "PermissionError: Cannot modify PIP id=38 with status Submitted. Only Draft PIPs can be edited."

  Scenario: MCP-PIP-17 add_change with invalid entity_type raises error
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |       42 |
      | change_type | ADD      |
      | entity_type | Potato   |
      | name        | Whatever |
    Then MCP returns error "ValueError: entity_type must be one of: Workflow, Activity, Skill, Agent, Artifact"

  Scenario: MCP-PIP-18 add_change ADD missing content raises error
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |       42 |
      | change_type | ADD      |
      | entity_type | Activity |
      | name        | New Act  |
      | parent_id   |       11 |
      | position    | append   |
      | content     |          |
    Then MCP returns error "ValueError: content is required for ADD changes"

  Scenario: MCP-PIP-19 add_change DROP missing rationale raises error
    When Cascade calls MCP tool "add_change" with:
      | pip_id      |       42 |
      | change_type | DROP     |
      | entity_type | Activity |
      | target_id   |       23 |
      | rationale   |          |
    Then MCP returns error "ValueError: rationale is required for DROP changes"
  # ============================================================================
  # edit_change (update an existing Change on a draft PIP)
  # ============================================================================

  Scenario: MCP-PIP-20 edit_change updates content on ADD Change
    Given PIP-42 has Change id=7 of type ADD with content "Old content"
    When Cascade calls MCP tool "edit_change" with:
      | pip_id    |                                                            42 |
      | change_id |                                                             7 |
      | content   | Ensure WCAG 2.1 AA compliance using axe-core and cypress-axe. |
    Then MCP returns success with updated content
    And Change id=7 content in DB is "Ensure WCAG 2.1 AA compliance using axe-core and cypress-axe."

  Scenario: MCP-PIP-21 edit_change updates position of ADD Change
    Given PIP-42 has Change id=7 of type ADD with position "append" on parent_id=11
    When Cascade calls MCP tool "edit_change" with:
      | pip_id    | 42 |
      | change_id |  7 |
      | after_id  | 22 |
    Then MCP returns success with position "after:22"

  Scenario: MCP-PIP-22 edit_change on non-Draft PIP raises error
    Given PIP-38 has status "Submitted" and Change id=5
    When Cascade calls MCP tool "edit_change" with:
      | pip_id    |      38 |
      | change_id |       5 |
      | content   | Updated |
    Then MCP returns error "PermissionError: Cannot modify PIP id=38 with status Submitted."

  Scenario: MCP-PIP-23 edit_change with change_id not belonging to pip raises error
    Given PIP-42 exists and Change id=99 belongs to PIP-38
    When Cascade calls MCP tool "edit_change" with:
      | pip_id    |  42 |
      | change_id |  99 |
      | content   | foo |
    Then MCP returns error "ValueError: Change id=99 does not belong to PIP id=42"
  # ============================================================================
  # remove_change (remove a Change from a draft PIP)
  # ============================================================================

  Scenario: MCP-PIP-24 remove_change deletes a Change from Draft PIP
    Given PIP-42 has 2 Changes: id=7 (ADD) and id=8 (ALTER)
    When Cascade calls MCP tool "remove_change" with:
      | pip_id    | 42 |
      | change_id |  7 |
    Then MCP returns success with deleted=True
    And PIP-42 now has 1 Change (id=8 only)

  Scenario: MCP-PIP-25 remove_change on non-Draft PIP raises error
    Given PIP-38 (Submitted) has Change id=5
    When Cascade calls MCP tool "remove_change" with:
      | pip_id    | 38 |
      | change_id |  5 |
    Then MCP returns error "PermissionError: Cannot modify PIP id=38 with status Submitted."
  # ============================================================================
  # submit_pip
  # ============================================================================

  Scenario: MCP-PIP-26 submit_pip transitions Draft PIP to Submitted
    Given PIP-42 has status "Draft" and 1 Change
    When Cascade calls MCP tool "submit_pip" with:
      | pip_id | 42 |
    Then MCP returns success with:
      | id     |        42 |
      | status | Submitted |
    And PIP-42 status in DB is "Submitted"
    And Galdr begins processing PIP-42 (status transitions to "Processing (Galdr)")

  Scenario: MCP-PIP-27 submit_pip on PIP with no Changes raises error
    Given PIP-42 has status "Draft" and 0 Changes
    When Cascade calls MCP tool "submit_pip" with:
      | pip_id | 42 |
    Then MCP returns error "ValueError: Cannot submit PIP id=42: it has no Changes. Add at least one Change before submitting."

  Scenario: MCP-PIP-28 submit_pip on already-Submitted PIP raises error
    Given PIP-38 has status "Submitted"
    When Cascade calls MCP tool "submit_pip" with:
      | pip_id | 38 |
    Then MCP returns error "PermissionError: PIP id=38 is already Submitted. Cannot resubmit."

  Scenario: MCP-PIP-29 submit_pip on Reviewed PIP raises error
    Given PIP-35 has status "Reviewed"
    When Cascade calls MCP tool "submit_pip" with:
      | pip_id | 35 |
    Then MCP returns error "PermissionError: PIP id=35 has status Reviewed and cannot be modified."

  Scenario: MCP-PIP-30 submit_pip on PIP not owned by current user raises error
    Given PIP-99 is owned by user "alex" and is Draft
    When Cascade calls MCP tool "submit_pip" with user context "maria":
      | pip_id | 99 |
    Then MCP returns error "PermissionError: PIP id=99 not found or not accessible"
  # ============================================================================
  # cancel_pip
  # ============================================================================

  Scenario: MCP-PIP-31 cancel_pip on Submitted PIP marks it cancelled
    Given PIP-38 has status "Submitted"
    When Cascade calls MCP tool "cancel_pip" with:
      | pip_id | 38 |
    Then MCP returns success with:
      | id     |        38 |
      | status | Cancelled |
    And PIP-38 status in DB is "Cancelled"
    And Galdr stops processing PIP-38 (if currently Processing, the Galdr job is discarded)

  Scenario: MCP-PIP-32 cancel_pip on Draft PIP marks it cancelled
    Given PIP-42 has status "Draft"
    When Cascade calls MCP tool "cancel_pip" with:
      | pip_id | 42 |
    Then MCP returns success with status "Cancelled"

  Scenario: MCP-PIP-33 cancel_pip on Reviewed PIP permanently cancels it
    Given PIP-35 has status "Reviewed"
    When Cascade calls MCP tool "cancel_pip" with:
      | pip_id | 35 |
    Then MCP returns success with:
      | id     |        35 |
      | status | Cancelled |
    And PIP-35 status in DB is "Cancelled"
    # Reviewed PIPs can be cancelled when the author decides not to proceed,
    # e.g. Galdr rejected all changes and a fresh redesign is warranted.
  # ============================================================================
  # revert_pip_to_draft
  # ============================================================================

  Scenario: MCP-PIP-40 revert_pip_to_draft on Reviewed PIP clears Galdr output and returns to Draft
    Given PIP-35 has status "Reviewed"
    And PIP-35 Changes have galdr_recommendation and galdr_reasoning populated
    When Cascade calls MCP tool "revert_pip_to_draft" with:
      | pip_id | 35 |
    Then MCP returns success with:
      | id       |   35 |
      | reverted | true |
    And PIP-35 status in DB is "Draft"
    And all PIP-35 Changes have galdr_recommendation="" and galdr_reasoning=""
    And PIP-35 galdr_holistic_assessment is ""
    # Primary use case: Galdr flagged NEEDS_CLARIFICATION — author pulls PIP back,
    # addresses feedback, and resubmits without creating a new PIP.

  Scenario: MCP-PIP-41 revert_pip_to_draft on Submitted PIP also succeeds
    Given PIP-38 has status "Submitted"
    When Cascade calls MCP tool "revert_pip_to_draft" with:
      | pip_id | 38 |
    Then MCP returns success with:
      | id       |   38 |
      | reverted | true |
    And PIP-38 status in DB is "Draft"

  Scenario: MCP-PIP-42 revert_pip_to_draft on Accepted PIP raises error
    Given PIP-30 has status "Accepted"
    When Cascade calls MCP tool "revert_pip_to_draft" with:
      | pip_id | 30 |
    Then MCP returns error "ValidationError: Cannot revert PIP to Draft from status 'accepted'."

  Scenario: MCP-PIP-43 revert_pip_to_draft on Rejected PIP raises error
    Given PIP-35 has status "Rejected"
    When Cascade calls MCP tool "revert_pip_to_draft" with:
      | pip_id | 35 |
    Then MCP returns error "ValidationError: Cannot revert PIP to Draft from status 'rejected'."

  Scenario: MCP-PIP-44 revert_pip_to_draft on PIP not owned by current user raises error
    Given PIP-99 is owned by user "alex" and has status "Reviewed"
    When Cascade calls MCP tool "revert_pip_to_draft" with user context "maria":
      | pip_id | 99 |
    Then MCP returns error "PermissionError: PIP id=99 not found or not accessible"
  # ============================================================================
  # cancel_pip (continued)
  # ============================================================================

  Scenario: MCP-PIP-34 cancel_pip on Accepted PIP raises error
    Given PIP-30 has status "Accepted"
    When Cascade calls MCP tool "cancel_pip" with:
      | pip_id | 30 |
    Then MCP returns error "PermissionError: PIP id=30 has status Accepted and cannot be cancelled."
  # ============================================================================
  # get_pip (view)
  # ============================================================================

  Scenario: MCP-PIP-35 get_pip returns full PIP detail including Changes
    Given PIP-42 has 2 Changes (one ADD, one ALTER)
    When Cascade calls MCP tool "get_pip" with:
      | pip_id | 42 |
    Then MCP returns:
      | field           | value                   |
      | id              |                      42 |
      | title           | Add Accessibility Audit |
      | summary         | Playbook lacks WCAG…    |
      | target_playbook | React Frontend Dev v1.0 |
      | status          | Draft                   |
      | submitted_by    | maria                   |
    And the response contains a "changes" array with 2 entries
    And Change #1 contains: change_type, entity_type, name, position, content
    And Change #2 contains: change_type, entity_type, target_id, target_name, content

  Scenario: MCP-PIP-36 get_pip on Reviewed PIP includes Galdr recommendations
    Given PIP-35 has status "Reviewed" and 1 Change with Galdr assessment
    When Cascade calls MCP tool "get_pip" with:
      | pip_id | 35 |
    Then MCP returns the PIP with status "Reviewed"
    And Change #1 in the response contains:
      | field                | value                                            |
      | galdr_recommendation | ACCEPT                                           |
      | galdr_reasoning      | Activity is redundant given auto-gen docs setup. |

  Scenario: MCP-PIP-37 get_pip on non-existent PIP raises error
    When Cascade calls MCP tool "get_pip" with:
      | pip_id | 9999 |
    Then MCP returns error "ValueError: PIP id=9999 not found"

  Scenario: MCP-PIP-38 get_pip on PIP owned by another user raises error
    Given PIP-99 is owned by user "alex"
    When Cascade calls MCP tool "get_pip" with user context "maria":
      | pip_id | 99 |
    Then MCP returns error "PermissionError: PIP id=99 not found or not accessible"
  # ============================================================================
  # FULL WORKFLOW — END-TO-END SCENARIO
  # ============================================================================

  Scenario: MCP-PIP-39 End-to-end: AI proposes and submits a structured PIP
    Given user "maria" has released playbook "React Frontend Dev v1.0" (id=1)
    # Step 1: Create draft PIP
    When Cascade calls MCP tool "create_pip" with:
      | playbook_id |                                             1 |
      | title       | Improve testing coverage                      |
      | summary     | Add accessibility checks alongside unit tests |
    Then MCP returns new PIP id with status "Draft"
    And let new_pip_id = <returned id>
    # Step 2: Add first Change — ADD Activity
    When Cascade calls MCP tool "add_change" with:
      | pip_id      | <new_pip_id>                                    |
      | change_type | ADD                                             |
      | entity_type | Activity                                        |
      | name        | Accessibility Audit                             |
      | after_id    |                                              22 |
      | content     | Run axe-core in jest; fail build on violations. |
    Then MCP confirms Change #1 added with change_type "ADD"
    # Step 3: Add second Change — ALTER existing Activity
    When Cascade calls MCP tool "add_change" with:
      | pip_id      | <new_pip_id>                                         |
      | change_type | ALTER                                                |
      | entity_type | Activity                                             |
      | target_id   |                                                   22 |
      | content     | Extend Component Testing to include cypress-axe E2E. |
    Then MCP confirms Change #2 added with change_type "ALTER"
    # Step 4: Review the PIP before submitting
    When Cascade calls MCP tool "get_pip" with pip_id=<new_pip_id>
    Then MCP returns PIP with 2 Changes and status "Draft"
    # Step 5: Submit the PIP
    When Cascade calls MCP tool "submit_pip" with pip_id=<new_pip_id>
    Then MCP returns PIP with status "Submitted"
    # Step 6: Poll for Galdr review (after some time)
    When Cascade calls MCP tool "get_pip" with pip_id=<new_pip_id>
    Then MCP returns PIP with status "Reviewed"
    And each Change has a galdr_recommendation (ACCEPT or REJECT) and galdr_reasoning
    # Step 7: List PIPs to verify state
    When Cascade calls MCP tool "list_pips" with status="Reviewed"
    Then MCP returns at least 1 PIP including the new PIP with status "Reviewed"
