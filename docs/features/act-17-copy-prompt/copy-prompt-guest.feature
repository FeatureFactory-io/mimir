@copy_prompt @guest_access
Feature: FOB-COPY-PROMPT-GUEST-1 Copy Prompt for guests and non-owners
  As an anonymous visitor (Bob) or non-owner (Maria)
  I want Copy Prompt on readable public playbook entities
  So that I can explore methodology content and paste it into my AI assistant before signing up

  Background:
    Given Mike owns a Public Released playbook "React Frontend Development"
    And the playbook has activity "Setup component structure"

  Scenario: FOB-COPY-PROMPT-GUEST-01 Guest copies prompt from public activity detail
    Given Bob is not logged in
    When Bob GET the activity detail URL for "Setup component structure"
    Then he sees data-testid "copy-prompt-btn"
    And he does not see [Edit Activity] or [Delete Activity]
    When he clicks [Copy Prompt]
    Then the clipboard receives the activity prompt

  Scenario: FOB-COPY-PROMPT-GUEST-02 Guest copies prompt from global activities list row
    Given Bob is not logged in
    When Bob opens "/activities/"
    Then released-public rows include data-testid "copy-prompt-btn-activity-<pk>"
    When he clicks [Copy Prompt] on "Setup component structure"
    Then the clipboard receives the activity prompt

  Scenario: FOB-COPY-PROMPT-GUEST-03 Guest cannot reach Copy Prompt for private playbook entities
    Given Bob is not logged in
    And an activity "Secret Activity" exists only in a Private Released playbook
    When Bob GET the activity detail URL for "Secret Activity"
    Then the response status is HTTP 404
    And no copy prompt control is rendered

  Scenario: FOB-COPY-PROMPT-GUEST-04 Guest cannot access PIP Copy Prompt
    Given Bob is not logged in
    When Bob GET "/pips/42/"
    Then the response status is HTTP 302 or HTTP 403
    # PIPs require authentication; Copy Prompt on PIP surfaces is authenticated only.

  Scenario: FOB-COPY-PROMPT-GUEST-05 Non-owner copies prompt on public released activity
    Given Maria is authenticated in FOB and is not the owner
    When Maria opens activity detail for "Setup component structure"
    Then she sees data-testid "copy-prompt-btn"
    And she does not see [Edit Activity] or [Delete Activity]
    When she clicks [Copy Prompt]
    Then the clipboard receives the activity prompt

  Scenario: FOB-COPY-PROMPT-GUEST-06 Owner sees Copy Prompt alongside edit actions on draft playbook
    Given Maria owns draft playbook "My Draft Playbook"
    And the playbook has activity "Draft Activity"
    When Maria opens that activity detail
    Then she sees data-testid "copy-prompt-btn"
    And she sees [Edit Activity] when can_edit is true
