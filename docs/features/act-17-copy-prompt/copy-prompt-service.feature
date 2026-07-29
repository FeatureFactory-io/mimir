@copy_prompt
Feature: FOB-COPY-PROMPT-SERVICE-1 Copy Prompt — server-built text
  As a developer
  I want CopyPromptService to assemble consistent AI instructions per entity type
  So that VIEW pages and list Actions copy identical text for the same record

  # Backend-only scenarios — pytest unit/integration against methodology/services/copy_prompt_service.py
  # Prompt style matches Use Cases sample commands: instruction line + raw Markdown body.

  Background:
    Given Mike owns playbook "React Frontend Development" (Public Released v1.2)

  Scenario: FOB-COPY-PROMPT-SERVICE-01 Activity prompt names playbook, workflow, ref, and guidance
    Given activity "Setup component structure" in workflow "Component Development"
    And the activity guidance Markdown is:
      """
      ## Overview
      Scaffold the component folder structure.
      """
    When CopyPromptService builds the activity prompt
    Then the prompt includes playbook name "React Frontend Development"
    And the prompt includes workflow name "Component Development"
    And the prompt includes activity name "Setup component structure"
    And the prompt includes the guidance Markdown unchanged
    And the prompt does NOT include rendered HTML

  Scenario: FOB-COPY-PROMPT-SERVICE-02 Skill prompt includes metadata and content
    Given skill "React Form Component" with capability_domain "GUI_FORM" and technology_stack "React+Redux"
    And the skill content Markdown is "## Patterns\nUse controlled inputs."
    When CopyPromptService builds the skill prompt
    Then the prompt includes playbook name "React Frontend Development"
    And the prompt includes capability domain "GUI_FORM"
    And the prompt includes technology stack "React+Redux"
    And the prompt includes the skill content Markdown unchanged

  Scenario: FOB-COPY-PROMPT-SERVICE-03 Agent prompt includes name and description
    Given agent "Cautious Developer (drdobbs-v2)" with description "Prefer small diffs."
    When CopyPromptService builds the agent prompt
    Then the prompt includes playbook name "React Frontend Development"
    And the prompt includes agent name "Cautious Developer (drdobbs-v2)"
    And the prompt includes description "Prefer small diffs."

  Scenario: FOB-COPY-PROMPT-SERVICE-04 Rule prompt includes slug, always_apply, and body
    Given rule "pytest-first" with slug "pytest-first" and always_apply true
    And the rule content is "Write tests before implementation."
    When CopyPromptService builds the rule prompt
    Then the prompt includes slug "pytest-first"
    And the prompt includes always_apply true
    And the prompt includes the rule content unchanged

  Scenario: FOB-COPY-PROMPT-SERVICE-05 Artifact prompt includes type, required flag, and description
    Given artifact "Component Design Document" of type Document and required true
    And the artifact description is "Spec for the component API."
    When CopyPromptService builds the artifact prompt
    Then the prompt includes artifact type Document
    And the prompt includes required status true
    And the prompt includes description "Spec for the component API."

  Scenario: FOB-COPY-PROMPT-SERVICE-06 PIP prompt includes summary and changes without Galdr text
    Given PIP-42 "Add Accessibility Audit" targets "React Frontend Development"
    And PIP-42 summary is "Add WCAG coverage to the playbook."
    And PIP-42 has changes:
      | type  | entity_type | target                |
      | ADD   | Activity    | Accessibility Audit   |
      | ALTER | Activity    | Component Testing     |
    When CopyPromptService builds the PIP prompt
    Then the prompt includes "PIP-42" and title "Add Accessibility Audit"
    And the prompt includes summary "Add WCAG coverage to the playbook."
    And the prompt lists both changes with type and target
    And the prompt does NOT include Galdr recommendation reasoning

  Scenario: FOB-COPY-PROMPT-SERVICE-07 Empty body still produces a usable prompt
    Given skill "Empty Skill" with blank content
    When CopyPromptService builds the skill prompt
    Then the prompt includes skill title "Empty Skill"
    And the prompt includes an instruction line for the AI assistant
    And the service does not raise an error
