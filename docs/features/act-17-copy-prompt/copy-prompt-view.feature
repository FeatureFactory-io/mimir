@wip @copy_prompt
Feature: FOB-COPY-PROMPT-VIEW-1 Copy Prompt on entity detail pages
  As a methodology author (Maria)
  I want [Copy Prompt] on every entity VIEW header toolbar
  So that I can paste playbook context into my IDE without opening MCP tools

  # Icon: Cursor SVG (static/images/cursor.svg) · Button: btn-outline-secondary · Tooltip: Copy prompt to use in your ADE
  # Placement: header toolbar before [Back]; visible regardless of can_edit.

  Background:
    Given Maria is authenticated in FOB
    And Mike owns playbook "React Frontend Development" (Public Released v1.2)

  Scenario: FOB-COPY-PROMPT-VIEW-01 Activity detail shows Copy Prompt in header actions
    Given Maria is on FOB-ACTIVITIES-VIEW_ACTIVITY-1 for "Setup component structure"
    Then she sees [Copy Prompt] with data-testid "copy-prompt-btn"
    And [Copy Prompt] is inside data-testid "activity-header-actions"
    And the button tooltip reads "Copy prompt to clipboard"

  Scenario: FOB-COPY-PROMPT-VIEW-02 Maria clicks Copy Prompt on activity detail
    Given Maria is on FOB-ACTIVITIES-VIEW_ACTIVITY-1 for "Setup component structure"
    And the page renders a hidden textarea data-testid "copy-prompt-text-activity-<pk>"
    When she clicks [Copy Prompt]
    Then the clipboard receives the server-built activity prompt
    And the button briefly shows a success state
    And she remains on FOB-ACTIVITIES-VIEW_ACTIVITY-1

  Scenario: FOB-COPY-PROMPT-VIEW-03 Skill detail header includes Copy Prompt
    Given Maria is on FOB-SKILLS-VIEW_SKILL-1 for "React Form Component"
    Then she sees data-testid "copy-prompt-btn" in the skill header toolbar

  Scenario: FOB-COPY-PROMPT-VIEW-04 Agent detail header includes Copy Prompt
    Given Maria is on FOB-AGENTS-VIEW_AGENT-1 for "Cautious Developer (drdobbs-v2)"
    Then she sees data-testid "copy-prompt-btn" in the agent header toolbar

  Scenario: FOB-COPY-PROMPT-VIEW-05 Rule detail header includes Copy Prompt
    Given Maria is on rule detail for "pytest-first"
    Then she sees data-testid "copy-prompt-btn" in the rule header toolbar

  Scenario: FOB-COPY-PROMPT-VIEW-06 Artifact detail header includes Copy Prompt
    Given Maria is on FOB-ARTIFACTS-VIEW_ARTIFACT-1 for "Component Design Document"
    Then she sees data-testid "copy-prompt-btn" in the artifact header toolbar

  Scenario: FOB-COPY-PROMPT-VIEW-07 Workflow detail header includes Copy Prompt
    Given Maria is on FOB-WORKFLOWS-VIEW_WORKFLOW-1 for "Component Development"
    Then she sees data-testid "copy-prompt-btn" in data-testid "workflow-header-actions"

  Scenario: FOB-COPY-PROMPT-VIEW-08 Phase detail header includes Copy Prompt
    Given Maria is on FOB-PHASES-VIEW_PHASE-1 for "Planning"
    Then she sees data-testid "copy-prompt-btn" in the phase header toolbar

  Scenario: FOB-COPY-PROMPT-VIEW-09 Playbook detail header includes Copy Prompt
    Given Maria is on FOB-PLAYBOOKS-VIEW_PLAYBOOK-1 for "React Frontend Development"
    Then she sees data-testid "copy-prompt-btn" in data-testid "playbook-header-actions"

  Scenario: FOB-COPY-PROMPT-VIEW-10 PIP detail header includes Copy Prompt
    Given Maria is on FOB-PIP-DETAIL-1 for PIP-42
    Then she sees data-testid "copy-prompt-btn" in data-testid "pip-detail-actions"

  Scenario: FOB-COPY-PROMPT-VIEW-11 Prompt text uses hidden textarea not data-copy attribute
    Given Maria is on any entity detail page with Copy Prompt
    Then a visually hidden textarea with data-testid "copy-prompt-text-*" holds the prompt
    And the prompt is not stored in a data-copy HTML attribute on the button

  Scenario: FOB-COPY-PROMPT-VIEW-12 Clipboard denial shows non-blocking error
    Given Maria is on FOB-ACTIVITIES-VIEW_ACTIVITY-1
    And the browser denies navigator.clipboard.writeText
    When she clicks [Copy Prompt]
    Then she sees a non-blocking error indication
    And the page does not navigate away

  Scenario: FOB-COPY-PROMPT-VIEW-13 Activity embed mode includes Copy Prompt
    Given Maria GET the activity detail URL with "?embed=1"
    Then the embed partial includes data-testid "copy-prompt-btn"
    And the embed does NOT include navbar or breadcrumbs
    When she clicks [Copy Prompt]
    Then the clipboard receives the full activity prompt

  Scenario: FOB-COPY-PROMPT-VIEW-14 Content Browser detail panel embed includes Copy Prompt
    Given Maria has the content browser detail panel open for an Activity node
    Then the embedded detail includes data-testid "copy-prompt-btn"
    When she clicks [Copy Prompt] inside the panel
    Then the clipboard receives the activity prompt without opening a new tab
