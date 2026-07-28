@guest_access
Feature: FOB-PLAYBOOKS-GUEST Anonymous Public Playbook Browse
  As an anonymous visitor (Bob)
  I want to discover and read released public playbooks without signing in
  So that I can evaluate methodology content before registering

  # Guest-readable playbook = visibility=public AND status=released only.
  # Mike owns the exemplar public released playbook "React Frontend Development".
  # Private, draft, active, and disabled public playbooks are never visible to guests.
  # Inaccessible playbooks return HTTP 404 (not 403) — no existence leak.

  Background:
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development"


  Scenario: FOB-PLAYBOOKS-GUEST-01 Landing Explore CTA navigates to public playbooks list
    Given Bob is on the FOB landing page at "/"
    Then he sees [Explore public playbooks] with data-testid "landing-cta-explore-playbooks"
    When he clicks [Explore public playbooks]
    Then he is redirected to "/playbooks/"


  Scenario: FOB-PLAYBOOKS-GUEST-02 Guest playbooks list shows released public playbooks only
    Given Bob opens "/playbooks/"
    Then he sees all primary navbar links from Home through PIPs
    And he sees a card for "React Frontend Development"
    And the card shows author "by Mike Chen"
    And he does not see an "Owned by you" or owned-playbooks section
    And he sees the guest banner with data-testid "guest-auth-banner"
    And the banner text includes "Sign in to create and edit playbooks"
    And he sees [Sign In] and [Register] in the guest banner
    And he does not see an actionable [Create New Playbook] button
      # If a Create affordance exists, it links to login rather than opening the wizard


  Scenario: FOB-PLAYBOOKS-GUEST-03 Guest views public playbook detail read-only
    Given Bob opens the playbook detail page for "React Frontend Development"
    Then he sees read-only Overview, Workflows, Activities, and related tabs
    And he can navigate between tabs without signing in
    And he does not see [Edit], [Delete], [Release], [Submit PIP], or [Export JSON]
    And he sees [Content Browser] linking to "/browser/<pk>/" for that playbook


  Scenario: FOB-PLAYBOOKS-GUEST-04 Guest cannot view private playbook detail
    Given Mike owns a Private Released playbook "Internal Security Playbook"
    When Bob GET "/playbooks/<private_pk>/"
    Then the response status is HTTP 404
    And Bob does not see playbook content
    And the response does not reveal whether the playbook exists or is private


  Scenario: FOB-PLAYBOOKS-GUEST-05 Guest drills down through public playbook entities read-only
    Given Bob opens the playbook detail page for "React Frontend Development"
    When he navigates to a workflow detail page within that playbook
    Then he sees workflow name, description, and activities list
    And he does not see [Edit Workflow], [Delete Workflow], or [Add Activity]
    When he navigates to an activity detail page within that playbook
    Then he sees activity guidance, dependencies, and linked artifacts
    And he does not see [Edit Activity], [Delete Activity], [Change Agent], or [Change Skill]
    When he navigates to an artifact detail page linked from that activity
    Then he sees artifact name, type, and template information read-only
    And he does not see [Edit Artifact] or [Delete Artifact]
    When he navigates to a rule detail page at "/playbooks/<pk>/rules/<rule_pk>/"
    Then he sees rule title and content read-only
    And he does not see [Edit Rule] or [Delete Rule]
    When he GET the rule embed URL with "?embed=1"
    Then the embed HTML loads without login redirect
    And the embed does not include navbar or mutation buttons


  Scenario: FOB-PLAYBOOKS-GUEST-06 Guest opens Content Browser from playbook header
    Given Bob opens the playbook detail page for "React Frontend Development"
    When he clicks [Content Browser] in the playbook header
    Then he is redirected to "/browser/<pk>/"
    And the three-panel Content Browser layout renders
    And the graph canvas loads with nodes and edges for that playbook


  Scenario: FOB-PLAYBOOKS-GUEST-07 Guest create playbook URL redirects to login
    When Bob GET "/playbooks/create/"
    Then he is redirected to the FOB login page
    And the redirect URL includes "?next=/playbooks/create/"


  Scenario: FOB-PLAYBOOKS-GUEST-08 Guest dashboard URL redirects to login
    When Bob GET "/dashboard/"
    Then he is redirected to the FOB login page
    And the redirect URL includes "?next=/dashboard/"
