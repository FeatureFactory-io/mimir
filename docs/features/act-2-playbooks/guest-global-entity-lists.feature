@guest_access @global_lists
Feature: FOB-GUEST-GLOBAL Anonymous Global Entity Lists
  As an anonymous visitor (Bob)
  I want to browse workflows, activities, and related entities across released public playbooks
  So that I can explore methodology building blocks without signing in

  # Guest-readable rows = entities whose parent playbook is visibility=public AND status=released.
  # Excludes: private playbooks; public draft, active, or disabled playbooks.
  # Global list routes are GET-only for guests; Create actions require login.

  Background:
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development" with workflows, activities, artifacts, skills, agents, rules, and phases
    And Mike owns a Private Released playbook "Internal Security Playbook" with entities that must not appear for guests
    And Mike owns a Public Draft playbook "Work In Progress Methodology" with entities that must not appear for guests


  Scenario: FOB-GUEST-GLOBAL-01 Guest global workflows list shows released-public rows only
    When Bob opens "/workflows/"
    Then he sees workflows from "React Frontend Development"
    And each row shows the parent playbook name "React Frontend Development"
    And he does not see workflows from "Internal Security Playbook"
    And he does not see workflows from "Work In Progress Methodology"
    And he does not see [Create New Workflow] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"


  Scenario: FOB-GUEST-GLOBAL-02 Guest global activities list shows released-public rows only
    When Bob opens "/activities/"
    Then he sees activities from "React Frontend Development"
    And he does not see activities from "Internal Security Playbook"
    And he does not see activities from "Work In Progress Methodology"
    And he does not see [Create New Activity] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"


  Scenario: FOB-GUEST-GLOBAL-03 Guest global artifacts list shows released-public rows only
    When Bob opens "/artifacts/"
    Then he sees artifacts from "React Frontend Development"
    And he does not see artifacts from "Internal Security Playbook"
    And he does not see artifacts from "Work In Progress Methodology"
    And he does not see [Create New Artifact] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"


  Scenario: FOB-GUEST-GLOBAL-04 Guest global skills list shows released-public rows only
    When Bob opens "/skills/"
    Then he sees skills from "React Frontend Development"
    And he does not see skills from "Internal Security Playbook"
    And he does not see skills from "Work In Progress Methodology"
    And he does not see [Create New Skill] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"


  Scenario: FOB-GUEST-GLOBAL-05 Guest global agents list shows released-public rows only
    When Bob opens "/agents/"
    Then he sees agents from "React Frontend Development"
    And he does not see agents from "Internal Security Playbook"
    And he does not see agents from "Work In Progress Methodology"
    And he does not see [Create New Agent] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"


  Scenario: FOB-GUEST-GLOBAL-06 Guest global rules list shows released-public rows only
    When Bob opens "/rules/"
    Then he sees rules from "React Frontend Development"
    And he does not see rules from "Internal Security Playbook"
    And he does not see rules from "Work In Progress Methodology"
    And he does not see [Create New Rule] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"


  Scenario: FOB-GUEST-GLOBAL-07 Guest global phases list shows released-public rows only
    When Bob opens "/phases/"
    Then he sees phases from "React Frontend Development"
    And he does not see phases from "Internal Security Playbook"
    And he does not see phases from "Work In Progress Methodology"
    And he does not see [Create New Phase] or equivalent create action
    And he sees the guest banner with data-testid "guest-auth-banner"
