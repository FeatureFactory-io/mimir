@wip @experts @karma
Feature: FOB-PROFILE-VIEW-1 Understand my contribution record

  Background:
    Given the CEDAR-RFP-01 baseline dataset

  Scenario: EXPERTS-PROFILE-01 Add contribution signals to Maria's existing profile
    Given Maria is authenticated
    When she opens "/auth/user/profile/"
    Then "profile-karma-card" is present
    And "profile-karma-total" reads "8,200"
    And the primary playbook category is "Design"
    And existing account/profile controls remain available

  Scenario: EXPERTS-PROFILE-03 Display four source rows that reconcile
    Given Maria is authenticated
    When she opens her own profile
    Then the source rows show 5000, 1600, 1200 and 400
    And their sum equals the displayed total 8200

  Scenario: EXPERTS-PROFILE-04 Keep own-profile account controls authenticated
    Given Bob is an anonymous visitor
    When he opens "/auth/user/profile/"
    Then he is redirected to the login page
    And no own-profile Karma or account token controls are shown
