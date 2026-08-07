@wip @experts @karma @pips
Feature: FOB-GALDR-CONTRIBUTION-SUMMARY-1 Galdr Refreshes Expert Contribution Summary
  As a PIP submitter (Maria)
  I want Galdr to refresh my contribution summary when I submit a PIP
  So that experts and visitors see an up-to-date expertise narrative

  Background:
    Given Maria is authenticated in FOB
    And Mike owns released playbook "React Frontend Development"

  Scenario: GALDR-SUMMARY-01 PIP submission triggers Galdr contribution summary refresh
    Given Maria is drafting PIP "Add Accessibility Audit" for "React Frontend Development"
    When Maria submits the PIP for review
    Then PIP status becomes "Processing (Galdr)"
    And Galdr refreshes Maria's contribution_summary while processing
    And Maria's contribution_summary is stored on her profile

  Scenario: GALDR-SUMMARY-02 Contribution summary surfaces on profile, expert view, and leaderboard hint
    Given Maria has an updated contribution_summary after PIP submission
    Then FOB-PROFILE-VIEW-1 shows data-testid="profile-contribution-summary" with the summary
    And FOB-EXPERT-VIEW-1 at /experts/mrodriguez/ shows data-testid="expert-contribution-summary" with the full summary
    And FOB-EXPERTS-LIST+FIND-1 shows a truncated expertise hint derived from the summary

  Scenario: GALDR-SUMMARY-03 Withdraw and resubmit refreshes summary without waiting for Admin
    Given PIP "Add Accessibility Audit" is in status "Reviewed"
    When Maria clicks [Withdraw] and resubmits the PIP
    Then Galdr refreshes Maria's contribution_summary during Processing
    And the refresh does not wait for Administrator acceptance

  Scenario: GALDR-SUMMARY-04 Expert without PIP submission shows numeric fallback hint
    Given Mike has total Karma 12450 but has never submitted a PIP
    When Elena is on /experts/?category=development
    Then the row for "Mike Chen" shows numeric expertise hint like "2 released · 47 copies"
    And data-testid="expert-contribution-summary" is absent on the leaderboard row
