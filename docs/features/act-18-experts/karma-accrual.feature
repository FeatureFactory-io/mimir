 @experts @karma
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

  Scenario Outline: KARMA-PIP-01 Award an accepted major ADD
    Given Maria's new PIP targets Hana's Accessible Forms Review version 2.0
    When an Administrator accepts its eligible ADD <entity> change
    Then Maria's total becomes 8700 and Design subtotal becomes 7700
    And the target playbook is version 3.0
    And the normal decision notification is captured locally
    Examples:
      | entity   |
      | Activity |
      | Skill    |
      | Artifact |

  Scenario Outline: KARMA-PIP-02 Award an accepted minor change
    When an Administrator accepts Maria's independent <operation> <entity> change
    Then Maria's total becomes 8300
    And 100 points are attributed to the target Design category
    Examples:
      | operation | entity                         |
      | ALTER     | Activity                       |
      | ALTER     | Skill                          |
      | ALTER     | Artifact                       |
      | ALTER     | Workflow                       |
      | ALTER     | Phase                          |
      | ALTER     | Agent                          |
      | ALTER     | Rule                           |
      | DROP      | Activity                       |
      | DROP      | Skill                          |
      | DROP      | Artifact                       |
      | DROP      | Workflow                       |
      | DROP      | Phase                          |
      | DROP      | Agent                          |
      | DROP      | Rule                           |
      | LINK      | supported existing relationship |
      | UNLINK    | supported existing relationship |
      | ADD       | Workflow                       |
      | ADD       | Phase                          |
      | ADD       | Agent                          |
      | ADD       | Rule                           |

  Scenario: KARMA-PIP-03 Award only accepted changes in a partial decision
    Given Maria's PIP contains one ADD Activity and one ALTER Activity
    When the Administrator accepts ADD and rejects ALTER
    Then Maria's total becomes 8700 rather than 8800

  Scenario: KARMA-PIP-04 Do not award draft, submitted or rejected-only proposals
    When Maria's PIP is draft, submitted, processing, reviewed or rejected without an accepted eligible change
    Then her total remains 8200

  Scenario Outline: KARMA-MCP-01 Credit eligible authenticated detail reads
    Given <consumer> has a valid MCP token and existing permission to read the independent <entity> fixture
    When the consumer reads that content using <tool>
    Then the actual authorized entity content is returned
    And the consumer total becomes <consumer_total> and target playbook author <author> becomes <author_total>
    And private content remains protected by its existing access checks
    Examples:
      | consumer | entity                           | tool         | consumer_total | author | author_total |
      | Maria    | Mike's Playbook                  | get_playbook | 8205           | Mike   | 12455        |
      | Maria    | Mike's Workflow                  | get_workflow | 8205           | Mike   | 12455        |
      | Maria    | Mike's Phase                     | get_phase    | 8205           | Mike   | 12455        |
      | Maria    | Mike's Activity                  | get_activity | 8205           | Mike   | 12455        |
      | Maria    | Mike's Skill                     | get_skill    | 8205           | Mike   | 12455        |
      | Maria    | Mike's Rule                      | get_rule     | 8205           | Mike   | 12455        |
      | Maria    | Mike's Agent                     | get_agent    | 8205           | Mike   | 12455        |
      | Maria    | Mike's Artifact                  | get_artifact | 8205           | Mike   | 12455        |
      | Mike     | Maria's historical Design PIP    | get_pip      | 12455          | Hana   | 5805         |
    # Mike is already the fixture's FOB administrator. For get_pip he reads
    # HIST-MARIA-DESIGN-01 as staff; Maria remains 8200. No permission is added.

  Scenario Outline: KARMA-MCP-03 Do not award self-fetch
    Given <consumer> has a valid MCP token and existing permission for <content>
    When the consumer successfully uses <tool> on that content
    Then the consumer total remains <total> and no paired author award is created
    Examples:
      | consumer | content                                         | tool         | total |
      | Mike     | Mike's Playbook                                 | get_playbook | 12450 |
      | Mike     | Mike's Workflow                                 | get_workflow | 12450 |
      | Mike     | Mike's Phase                                    | get_phase    | 12450 |
      | Mike     | Mike's Activity                                 | get_activity | 12450 |
      | Mike     | Mike's Skill                                    | get_skill    | 12450 |
      | Mike     | Mike's Rule                                     | get_rule     | 12450 |
      | Mike     | Mike's Agent                                    | get_agent    | 12450 |
      | Mike     | Mike's Artifact                                 | get_artifact | 12450 |
      | Mike     | Maria's historical PIP targeting Mike's playbook | get_pip      | 12450 |
      | Maria    | Maria's historical PIP targeting Hana's playbook | get_pip      | 8200  |
    # A PIP fetch is self-consumption if the caller is its creator OR its
    # target playbook's author. Otherwise the author award goes to the target
    # playbook author, never to the PIP creator. Existing read permission gates it.

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
    Then exactly one award exists per applicable recipient
    And acceptance has one submitter award while eligible other-person consumption has consumer and author awards
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
