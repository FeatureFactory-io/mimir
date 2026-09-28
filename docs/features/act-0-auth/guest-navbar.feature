@guest_access @navigation
Feature: FOB-GUEST-NAV Anonymous Realm Bar and App Sidebar
  As an anonymous visitor (Bob)
  I want the FeatureFactory realm bar and the full Mimir app sidebar on every page
  So that I can explore public methodology surfaces before registering

  # Realm bar = FeatureFactory, Mimir, Huginn, Yggdrasil, Heimdall.
  # App sidebar = Home through PIPs (same destinations as the former primary navbar).
  # Auth-only destinations (Home, Teams, PIPs) redirect to login when clicked.
  # Right-side authenticated chrome (global search, notifications bell, user menu)
  # remains hidden for guests; Register and Login buttons are shown instead.

  Background:
    Given Bob is not logged in


  Scenario: GUEST-NAV-01 Anonymous landing shows realm bar, sidebar, and auth buttons
    Given Bob is on the FOB landing page at "/"
    Then he sees realm links FeatureFactory, Mimir, Huginn, Yggdrasil, and Heimdall
    And he sees all app sidebar links from Home through PIPs
    And he sees [Register] with data-testid "register-link"
    And he sees [Login] with data-testid "login-link"
    And he does not see global search with data-testid "global-search-input"
    And he does not see the notification bell with data-testid "notification-bell"
    And he does not see the user menu with data-testid "user-display"


  Scenario: GUEST-NAV-02 Guest playbooks list highlights Playbooks sidebar item
    Given Bob opens "/playbooks/"
    Then he sees all app sidebar links from Home through PIPs
    And the "Playbooks" link in the app sidebar has "active" class
    And he sees [Register] with data-testid "register-link"
    And he sees [Login] with data-testid "login-link"


  Scenario: GUEST-NAV-03 Guest Home link redirects to login
    When Bob GET "/dashboard/"
    Then he is redirected to the FOB login page
    And the redirect URL includes "?next=/dashboard/"


  Scenario: GUEST-NAV-04 Guest Teams link redirects to login
    When Bob GET "/teams/"
    Then he is redirected to the FOB login page
    And the redirect URL includes "?next=/teams/"


  Scenario: GUEST-NAV-05 Guest PIPs link redirects to login
    When Bob GET "/pips/"
    Then he is redirected to the FOB login page
    And the redirect URL includes "?next=/pips/"
