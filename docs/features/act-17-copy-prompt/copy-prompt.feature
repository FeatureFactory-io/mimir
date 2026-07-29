@copy_prompt
Feature: FOB-COPY-PROMPT-1 Copy Prompt — server-built AI instructions
  As a methodology author (Maria) or visitor (Bob)
  I want a [Copy Prompt] control on entity view pages and list-row Actions
  So that I can paste playbook context into my IDE or AI assistant without retyping

  # Implementation: Option B — CopyPromptService in methodology/services/ builds prompt text;
  # views pass copy_prompt_text to templates; shared partial + JS call navigator.clipboard.writeText.
  #
  # Prompt style (instruction + content), aligned with methodology/use_cases.html:
  #   "Read the '<ref> <name>' <entity_type> from playbook '<playbook>' …"
  # followed by raw Markdown body fields (guidance, content, description, etc.).
  #
  # Out of scope: Teams, Profile API token copy (act-14), Use Cases sample commands,
  # PIP admin-review screen, create/edit/delete forms, search-result links without Actions.
  #
  # Surfaces:
  #   A) View/detail page header toolbars (and embed ?embed=1 variants)
  #   B) List/table Actions columns (global + playbook/workflow scoped lists)
  #   C) Nested tables on detail pages (playbook Workflows tab, phase detail activities)
  #
  # data-testid convention:
  #   View header:  copy-prompt-btn
  #   List row:     copy-prompt-btn-<entity_type>-<pk>  (e.g. copy-prompt-btn-activity-42)
  #   Hidden store: copy-prompt-text-<entity_type>-<pk> (textarea, visually hidden)

  Background:
    Given Maria is authenticated in FOB
    And Mike owns playbook "React Frontend Development" (Public Released v1.2)
    And the playbook has representative entities for each type below

  # ============================================================================
  # 1 — SERVICE: prompt content (pytest integration / unit; one scenario per type)
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-01 Activity prompt includes playbook, workflow, ref, and guidance
    Given activity "Setup component structure" in workflow "Component Development"
    When CopyPromptService builds the activity prompt
    Then the prompt names playbook "React Frontend Development"
    And the prompt names workflow "Component Development"
    And the prompt includes activity reference label or name "Setup component structure"
    And the prompt includes the raw guidance Markdown unchanged
    And the prompt does NOT include rendered HTML from the Markdown pipeline

  Scenario: FOB-COPY-PROMPT-02 Skill prompt includes metadata and content
    Given skill "React Form Component" with capability_domain "GUI_FORM" and technology_stack "React+Redux"
    When CopyPromptService builds the skill prompt
    Then the prompt names the parent playbook
    And the prompt includes capability domain and technology stack when present
    And the prompt includes the raw skill content Markdown

  Scenario: FOB-COPY-PROMPT-03 Agent prompt includes description and playbook context
    Given agent "Cautious Developer (drdobbs-v2)"
    When CopyPromptService builds the agent prompt
    Then the prompt names the parent playbook
    And the prompt includes the agent name and raw description text

  Scenario: FOB-COPY-PROMPT-04 Rule prompt includes slug, always_apply, and body
    Given rule "pytest-first" with slug "pytest-first" and always_apply true
    When CopyPromptService builds the rule prompt
    Then the prompt names the parent playbook
    And the prompt includes slug and always_apply flag
    And the prompt includes the raw rule content Markdown

  Scenario: FOB-COPY-PROMPT-05 Artifact prompt includes type, required flag, and description
    Given artifact "Component Design Document" of type Document
    When CopyPromptService builds the artifact prompt
    Then the prompt names the parent playbook
    And the prompt includes artifact type and required status
    And the prompt includes the raw description text

  Scenario: FOB-COPY-PROMPT-06 Workflow prompt includes description and ordered activity index
    Given workflow "Component Development" with 8 activities
    When CopyPromptService builds the workflow prompt
    Then the prompt names the parent playbook
    And the prompt includes workflow description when present
    And the prompt lists activity names in order (names/refs only — not full guidance bodies)

  Scenario: FOB-COPY-PROMPT-07 Phase prompt includes description and assigned activities
    Given phase "Planning" in workflow "Component Development" with 3 activities
    When CopyPromptService builds the phase prompt
    Then the prompt names playbook and workflow
    And the prompt includes phase order and description when present
    And the prompt lists assigned activity names in order

  Scenario: FOB-COPY-PROMPT-08 Playbook prompt includes overview and structure summary
    Given playbook "React Frontend Development" with description and entity counts
    When CopyPromptService builds the playbook prompt
    Then the prompt includes playbook name, version, and status
    And the prompt includes the raw description Markdown when present
    And the prompt summarizes workflow names and top-level counts (workflows, activities, skills, rules)
    And the prompt does NOT embed full guidance for every activity (too large for clipboard)

  Scenario: FOB-COPY-PROMPT-09 PIP prompt includes target playbook, summary, and change list
    Given PIP-42 "Add Accessibility Audit" targeting "React Frontend Development" with 2 changes
    When CopyPromptService builds the PIP prompt
    Then the prompt includes PIP id, title, status, and target playbook
    And the prompt includes the summary rationale
    And the prompt lists each change with type, entity_type, and target name
    And the prompt does NOT include Galdr reasoning text (review context stays in UI)

  Scenario: FOB-COPY-PROMPT-10 Empty body fields produce a usable prompt without error
    Given skill "Empty Skill" with blank content
    When CopyPromptService builds the skill prompt
    Then the prompt still includes instruction line and entity identifiers
    And the prompt notes that content is empty or omits the body section gracefully

  # ============================================================================
  # 2 — SHARED UI: button, clipboard, feedback
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-11 View page shows Copy Prompt in header actions
    Given Maria is on FOB-ACTIVITIES-VIEW_ACTIVITY-1 for "Setup component structure"
    Then she sees [Copy Prompt] with data-testid "copy-prompt-btn"
    And the button uses icon fa-regular fa-copy (or fa-solid fa-copy)
    And the button tooltip reads "Copy prompt to clipboard"
    And [Copy Prompt] is visible regardless of can_edit (read-only viewers included)

  Scenario: FOB-COPY-PROMPT-12 Click Copy Prompt writes server-built text to clipboard
    Given Maria is on an entity detail page with copy_prompt_text rendered
    When she clicks [Copy Prompt]
    Then navigator.clipboard.writeText is called with the exact copy_prompt_text value
    And the button briefly shows a success state (check icon or "Copied!" tooltip)
    And the page does not navigate away

  Scenario: FOB-COPY-PROMPT-13 Prompt text is stored in a hidden textarea not a data-copy attribute
    Given Maria is on an entity detail page
    Then a visually hidden textarea data-testid matching "copy-prompt-text-*" holds the prompt
    And the prompt text is not duplicated in a data-copy HTML attribute (avoids size/escape limits)

  Scenario: FOB-COPY-PROMPT-14 Clipboard failure is handled without breaking the page
    Given Maria is on an entity detail page
    And the browser denies clipboard.writeText
    When she clicks [Copy Prompt]
    Then she sees a non-blocking error indication (tooltip or toast)
    And the console logs a copy failure message without secrets

  # ============================================================================
  # 3 — VIEW PAGES: one visibility scenario per entity type (copy behavior = §12)
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-20 Activity detail header includes Copy Prompt
    Given Maria is on FOB-ACTIVITIES-VIEW_ACTIVITY-1
    Then data-testid "copy-prompt-btn" is in data-testid "activity-header-actions"

  Scenario: FOB-COPY-PROMPT-21 Skill detail header includes Copy Prompt
    Given Maria is on FOB-SKILLS-VIEW_SKILL-1
    Then data-testid "copy-prompt-btn" is visible in the skill header toolbar

  Scenario: FOB-COPY-PROMPT-22 Agent detail header includes Copy Prompt
    Given Maria is on FOB-AGENTS-VIEW_AGENT-1
    Then data-testid "copy-prompt-btn" is visible in the agent header toolbar

  Scenario: FOB-COPY-PROMPT-23 Rule detail header includes Copy Prompt
    Given Maria is on rule detail for "pytest-first"
    Then data-testid "copy-prompt-btn" is visible in the rule header toolbar

  Scenario: FOB-COPY-PROMPT-24 Artifact detail header includes Copy Prompt
    Given Maria is on FOB-ARTIFACTS-VIEW_ARTIFACT-1
    Then data-testid "copy-prompt-btn" is visible in the artifact header toolbar

  Scenario: FOB-COPY-PROMPT-25 Workflow detail header includes Copy Prompt
    Given Maria is on FOB-WORKFLOWS-VIEW_WORKFLOW-1
    Then data-testid "copy-prompt-btn" is in data-testid "workflow-header-actions"

  Scenario: FOB-COPY-PROMPT-26 Phase detail header includes Copy Prompt
    Given Maria is on FOB-PHASES-VIEW_PHASE-1
    Then data-testid "copy-prompt-btn" is visible in the phase header toolbar

  Scenario: FOB-COPY-PROMPT-27 Playbook detail header includes Copy Prompt
    Given Maria is on FOB-PLAYBOOKS-VIEW_PLAYBOOK-1
    Then data-testid "copy-prompt-btn" is in data-testid "playbook-header-actions"

  Scenario: FOB-COPY-PROMPT-28 PIP detail header includes Copy Prompt
    Given Maria is on FOB-PIP-DETAIL-1 for PIP-42
    Then data-testid "copy-prompt-btn" is in data-testid "pip-detail-actions"

  # ============================================================================
  # 4 — LIST / TABLE ACTIONS: Copy Prompt beside existing View (eye) buttons
  #     Same clipboard behavior as view pages; prompt content identical for same entity.
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-30 Workflow-scoped activities list row Actions
    Given Maria is on FOB-ACTIVITIES-LIST+FIND-1
    Then each activity row Actions cell includes data-testid "copy-prompt-btn-activity-<pk>"
    When she clicks [Copy Prompt] on "Setup component structure" without opening detail
    Then the clipboard receives the same text as FOB-COPY-PROMPT-01

  Scenario: FOB-COPY-PROMPT-31 Playbook-scoped activities list row Actions
    Given Maria is on the playbook activities list for "React Frontend Development"
    Then each row includes data-testid "copy-prompt-btn-activity-<pk>"

  Scenario: FOB-COPY-PROMPT-32 Global activities list row Actions
    Given Maria is on "/activities/"
    Then each row includes data-testid "copy-prompt-btn-activity-<pk>"

  Scenario: FOB-COPY-PROMPT-33 Playbook-scoped skills list row Actions
    Given Maria is on FOB-SKILLS-LIST+FIND-1 for the playbook
    Then each row includes data-testid "copy-prompt-btn-skill-<pk>"

  Scenario: FOB-COPY-PROMPT-34 Global skills list row Actions
    Given Maria is on "/skills/"
    Then each row includes data-testid "copy-prompt-btn-skill-<pk>"

  Scenario: FOB-COPY-PROMPT-35 Playbook-scoped agents list row Actions
    Given Maria is on agents list for the playbook
    Then each row includes data-testid "copy-prompt-btn-agent-<pk>"

  Scenario: FOB-COPY-PROMPT-36 Global agents list row Actions
    Given Maria is on "/agents/"
    Then each row includes data-testid "copy-prompt-btn-agent-<pk>"

  Scenario: FOB-COPY-PROMPT-37 Global rules list row Actions
    Given Maria is on "/rules/"
    Then each row includes data-testid "copy-prompt-btn-rule-<pk>"

  Scenario: FOB-COPY-PROMPT-38 Playbook-scoped rules list row Actions
    Given Maria is on playbook rules list for "React Frontend Development"
    Then each row includes data-testid "copy-prompt-btn-rule-<pk>"

  Scenario: FOB-COPY-PROMPT-39 Playbook-scoped artifacts list row Actions
    Given Maria is on artifacts list for the playbook
    Then each row includes data-testid "copy-prompt-btn-artifact-<pk>"

  Scenario: FOB-COPY-PROMPT-40 Global artifacts list row Actions
    Given Maria is on "/artifacts/"
    Then each row includes data-testid "copy-prompt-btn-artifact-<pk>"

  Scenario: FOB-COPY-PROMPT-41 Playbook-scoped workflows list row Actions
    Given Maria is on FOB-WORKFLOWS-LIST+FIND-1
    Then each row includes data-testid "copy-prompt-btn-workflow-<pk>"

  Scenario: FOB-COPY-PROMPT-42 Global workflows list row Actions
    Given Maria is on "/workflows/"
    Then each row includes data-testid "copy-prompt-btn-workflow-<pk>"

  Scenario: FOB-COPY-PROMPT-43 Playbook-scoped phases list row Actions
    Given Maria is on FOB-PHASES-LIST+FIND-1
    Then each row includes data-testid "copy-prompt-btn-phase-<pk>"

  Scenario: FOB-COPY-PROMPT-44 Global phases list row Actions
    Given Maria is on "/phases/"
    Then each row includes data-testid "copy-prompt-btn-phase-<pk>"

  Scenario: FOB-COPY-PROMPT-45 PIP list row Actions
    Given Maria is on FOB-PIP-LIST-1
    Then each PIP row Actions cell includes data-testid "copy-prompt-btn-pip-<pk>"
    And [Copy Prompt] sits beside the existing View (eye) button

  Scenario: FOB-COPY-PROMPT-46 Playbook detail Workflows tab nested table Actions
    Given Maria is on FOB-PLAYBOOKS-VIEW_PLAYBOOK-1 Workflows tab
    Then each workflow row in data-testid "workflows-table" includes copy-prompt-btn-workflow-<pk>

  Scenario: FOB-COPY-PROMPT-47 Phase detail nested activities table Actions
    Given Maria is on FOB-PHASES-VIEW_PHASE-1 with assigned activities
    Then each activity row in the phase activities table includes copy-prompt-btn-activity-<pk>

  # Playbooks list uses cards (not a table) — Copy Prompt is view-page only for playbooks unless cards gain an action later.

  # ============================================================================
  # 5 — EMBED + CONTENT BROWSER
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-50 Embed mode includes Copy Prompt without outer chrome
    Given Maria GET an activity detail URL with "?embed=1"
    Then the embed partial includes data-testid "copy-prompt-btn"
    And the embed does NOT include navbar or breadcrumbs
    And Copy Prompt still copies the full server-built prompt

  Scenario: FOB-COPY-PROMPT-51 Content Browser detail panel embed includes Copy Prompt
    Given Maria has the content browser detail panel open for an Activity node
    Then the embedded detail includes data-testid "copy-prompt-btn"
    When she clicks [Copy Prompt] inside the panel
    Then the clipboard receives the activity prompt without opening a new tab

  Scenario: FOB-COPY-PROMPT-52 Copy Prompt on full page matches copy from list row for same entity
    Given activity "Setup component structure" exists
    When Maria copies from the global activities list row
    And Maria copies from the activity detail header
    Then both clipboard payloads are identical

  # ============================================================================
  # 6 — GUEST ACCESS (@guest_access)
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-60 Guest copies prompt from public released activity detail
    Given Bob is not logged in
    And "Setup component structure" is in a Public Released playbook
    When Bob GET the activity detail URL
    Then he sees data-testid "copy-prompt-btn"
    And he does not see edit or delete actions
    When he clicks [Copy Prompt]
    Then the clipboard receives the activity prompt

  Scenario: FOB-COPY-PROMPT-61 Guest copies prompt from global list row
    Given Bob is not logged in
    When Bob opens "/activities/"
    Then released-public rows include data-testid "copy-prompt-btn-activity-<pk>"
    When he clicks [Copy Prompt] on a visible row
    Then the clipboard receives the activity prompt

  Scenario: FOB-COPY-PROMPT-62 Guest cannot reach Copy Prompt for private playbook entities
    Given Bob is not logged in
    And an activity exists only in a Private Released playbook
    When Bob GET the activity detail URL
    Then the response status is HTTP 404
    And no copy prompt control is rendered

  Scenario: FOB-COPY-PROMPT-63 Guest cannot copy PIP prompts
    Given Bob is not logged in
    When Bob GET "/pips/<pk>/"
    Then the response status is HTTP 302 or HTTP 403
    # PIPs require authentication; Copy Prompt on PIP surfaces is owner/authenticated only.

  # ============================================================================
  # 7 — ACCESS CONTROL (authenticated non-owner)
  # ============================================================================

  Scenario: FOB-COPY-PROMPT-70 Non-owner can Copy Prompt on public released playbook entities
    Given Mike owns a Public Released playbook "React Frontend Development"
    And Maria is authenticated and is not the owner
    When Maria opens activity detail in that playbook
    Then she sees data-testid "copy-prompt-btn"
    And she does not see edit or delete actions

  Scenario: FOB-COPY-PROMPT-71 Owner can Copy Prompt on draft playbook entities
    Given Maria owns draft playbook "My Draft Playbook" with an activity
    When Maria opens that activity detail
    Then she sees data-testid "copy-prompt-btn"
    And she also sees edit actions when can_edit is true
