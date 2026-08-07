@wip @experts @karma
Feature: FOB-KARMA-ACCRUAL-1 Karma Points Accrual
  As a playbook author, contributor, or learner
  I earn Karma when I release playbooks, improve playbooks via PIPs, or consume methodology content
  So that community reputation reflects methodology impact

  # ── Release v1.0 ────────────────────────────────────────────────────────

  Scenario: KARMA-RELEASE-01 Author earns 5000 Karma on first Release v1.0
    Given Mike is authenticated in FOB
    And Mike owns draft playbook "React Frontend Development" in category "Development"
    When Mike clicks [Release] and confirms release to v1.0
    Then playbook status is "Released" at version 1.0
    And Mike's total Karma increases by 5000
    And Mike sees toast "You earned 5,000 Karma for releasing React Frontend Development"
    And the Karma is attributed to category "Development"

  Scenario: KARMA-RELEASE-02 No Karma on v2.0 release after PIP acceptance
    Given Mike owns released playbook "React Frontend Development" at version 1.0
    And a PIP acceptance publishes version 2.0
    When version 2.0 is published
    Then Mike's total Karma does not increase by 5000

  # ── PIP acceptance ──────────────────────────────────────────────────────

  Scenario: KARMA-PIP-01 Submitter earns 500 for accepted ADD Activity change
    Given Maria submitted PIP "Add Accessibility Audit" with ADD Activity change
    When Administrator accepts the PIP and applies the ADD change
    Then Maria's total Karma increases by 500
    And Karma is attributed to the target playbook category

  Scenario: KARMA-PIP-02 Submitter earns 100 for accepted ALTER change
    Given Maria submitted PIP with ALTER Activity change
    When Administrator accepts the ALTER change
    Then Maria's total Karma increases by 100

  Scenario: KARMA-PIP-03 Partial acceptance awards Karma only for accepted changes
    Given Maria submitted PIP with 2 changes: ADD Activity and ALTER Activity
    When Administrator accepts ADD and rejects ALTER
    Then Maria's total Karma increases by 500 only

  Scenario: KARMA-PIP-04 No Karma for Draft or rejected-only PIPs
    Given Maria has a Draft PIP
    When the PIP remains Draft or is fully Rejected
    Then Maria earns no Karma from that PIP

  # ── Copy to ADE (GUI) ─────────────────────────────────────────────────────

  Scenario: KARMA-COPY-01 Authenticated copy earns consumer and author Karma
    Given Maria is authenticated in FOB
    And Mike owns public released playbook "React Frontend Development"
    And the playbook has activity "Setup component structure"
    When Maria opens the activity detail and clicks [Copy Prompt]
    Then the clipboard receives the activity prompt
    And Maria's total Karma increases by 5
    And Mike's total Karma increases by 5

  Scenario: KARMA-COPY-02 Guest copy works but accrues no Karma
    Given Bob is not logged in
    And Mike owns public released playbook "React Frontend Development"
    When Bob clicks [Copy Prompt] on a public released activity
    Then the clipboard receives the activity prompt
    And Bob's Karma does not change
    And Mike's Karma does not change

  Scenario: KARMA-COPY-03 Self-copy earns no Karma
    Given Mike is authenticated in FOB
    And Mike owns activity "Setup component structure"
    When Mike clicks [Copy Prompt] on his own activity
    Then the clipboard receives the activity prompt
    And Mike's total Karma does not increase

  # ── MCP get_* reads ───────────────────────────────────────────────────────

  Scenario: KARMA-MCP-01 Authenticated get_activity earns consumer and author Karma
    Given Maria is authenticated in FOB with a valid MCP token
    And Mike owns public released activity "Setup component structure"
    When Maria calls MCP tool "get_activity" for that activity
    Then Maria's total Karma increases by 5
    And Mike's total Karma increases by 5

  Scenario: KARMA-MCP-02 list_activities earns no Karma
    Given Maria is authenticated in FOB with a valid MCP token
    When Maria calls MCP tool "list_activities"
    Then Maria's total Karma does not change
    And no playbook author Karma is awarded

  # ── export_workflow_to_local ──────────────────────────────────────────────

  Scenario: KARMA-EXPORT-01 Authenticated export earns consumer and author Karma
    Given Maria is authenticated in FOB with a valid MCP token
    And Mike owns workflow "Frontend Development" in "React Frontend Development"
    When Maria calls MCP tool "export_workflow_to_local" for that workflow
    Then Maria's total Karma increases by 5
    And Mike's total Karma increases by 5
    And Karma accrues once per export call regardless of file count

  Scenario: KARMA-EXPORT-02 Self-export earns no Karma
    Given Mike is authenticated in FOB with a valid MCP token
    And Mike owns workflow "Frontend Development"
    When Mike calls MCP tool "export_workflow_to_local" for his own workflow
    Then Mike's total Karma does not increase

  Scenario: KARMA-EXPORT-03 import_workflow_from_local earns no Karma
    Given Maria is authenticated in FOB with a valid MCP token
    When Maria calls MCP tool "import_workflow_from_local"
    Then Maria's total Karma does not change
    And no author Karma is awarded
