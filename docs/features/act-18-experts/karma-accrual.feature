@wip @experts @karma
Feature: FOB-KARMA-ACCRUAL-1 Award contribution points for eligible events
  Each case restores CEDAR-RFP-01 independently. Historical import is not a user event.

  Background:
    Given the CEDAR-RFP-01 baseline dataset

  Scenario: KARMA-RELEASE-01 Award the first released playbook once
    Given Nora owns draft Accessible Workshop Starter in Product
    When she first releases it as version 1.0
    Then Nora's total changes from 0 to 5000 in Product
    And the Product ranking is Alex 5400 followed by Nora 5000
    And she sees "You earned 5,000 Karma for releasing Accessible Workshop Starter"

  Scenario: KARMA-RELEASE-02 Do not repeat the first-release award on later versions
    Given a playbook has already earned its first-release award
    When an accepted PIP publishes its next major version
    Then its author receives no additional 5000 first-release points

  Scenario: KARMA-PIP-01 Award an accepted ADD Activity
    Given Maria's new PIP targets Hana's Accessible Forms Review version 2.0
    When an Administrator accepts its Screen Reader Error Recovery ADD Activity
    Then Maria's total becomes 8700 and Design subtotal becomes 7700
    And the target playbook is version 3.0
    And the normal decision notification is captured locally

  Scenario: KARMA-PIP-02 Award an accepted ALTER Activity
    When an Administrator accepts Maria's independent ALTER Activity change
    Then Maria's total becomes 8300
    And 100 points are attributed to the target Design category

  Scenario: KARMA-PIP-03 Award only accepted changes in a partial decision
    Given Maria's PIP contains one ADD Activity and one ALTER Activity
    When the Administrator accepts ADD and rejects ALTER
    Then Maria's total becomes 8700 rather than 8800

  Scenario: KARMA-PIP-04 Do not award draft, submitted or rejected-only proposals
    When Maria's PIP is draft, submitted, processing, reviewed or rejected without an accepted eligible change
    Then her total remains 8200

  Scenario: KARMA-COPY-01 Credit a successful authenticated copy to both parties
    Given Maria is authenticated
    When she successfully copies Mike's public released activity 6203
    Then the clipboard receives the actual activity prompt
    And Maria's total becomes 8205 and Mike's becomes 12455
    And both awards belong to Development

  Scenario: KARMA-COPY-02 Let guests copy without creating an award
    Given Bob is an anonymous visitor
    When he copies Mike's public released activity 6203
    Then the clipboard receives the actual activity prompt
    And Mike remains at 12450
    And no account or Karma award is created for Bob

  Scenario: KARMA-COPY-03 Do not award self-copy
    Given Mike is authenticated
    When he copies his own activity 6203
    Then the clipboard receives the actual activity prompt
    And Mike remains at 12450

  Scenario: KARMA-MCP-01 Credit an eligible authenticated content read
    Given Maria has a valid MCP token
    When she reads Mike's public released activity 6203 using get_activity
    Then the real activity content is returned
    And Maria's total becomes 8205 and Mike's becomes 12455
    And private content remains protected by its access checks

  Scenario: KARMA-MCP-02 Do not award collection listings
    Given Maria has a valid MCP token
    When she calls list_activities
    Then Maria remains at 8200 and Mike remains at 12450

  Scenario: KARMA-EXPORT-01 Credit one eligible export call regardless of file count
    Given Maria has a valid MCP token
    When she exports Mike's public released workflow 6202 into multiple local files
    Then the actual export files are written within the authorized export root
    And Maria's total becomes 8205 and Mike's becomes 12455
    And the award is per successful call rather than per generated file

  Scenario: KARMA-EXPORT-02 Do not award self-export
    Given Mike has a valid MCP token
    When he exports his own workflow 6202
    Then his total remains 12450

  Scenario: KARMA-EXPORT-03 Do not award import
    Given Maria has a valid MCP token
    When she imports a workflow
    Then Maria remains at 8200 and Mike remains at 12450

  Scenario: KARMA-EVENT-01 Do not double-apply an event on write retry
    Given one accepted eligible change or successful consumption has a stable event identity
    When recording that same event is retried
    Then exactly one pair of applicable ledger awards exists
    And a later intentional consumption is treated as a new event

  Scenario: KARMA-EVENT-02 Do not award failed or unauthorized consumption
    When a private read is denied or a clipboard write or export fails
    Then no consumption award is created for either party

  Scenario Outline: KARMA-CATEGORY-01 Resolve primary-category ties
    Given the isolated <variant> data
    When the user's primary playbook category is projected
    Then the result is <category>
    Examples:
      | variant | category    |
      | TIE01   | Development |
      | TIE02   | Design      |
