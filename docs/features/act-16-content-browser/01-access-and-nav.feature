Feature: FOB-CONTENT-BROWSER-ACCESS Content Browser Access and Navigation
  As a methodology author (Maria) or team member
  I want to open the Content Browser from a playbook I am viewing
  So that I can explore that playbook's entity graph without picking a playbook first

  Background:
    Given Maria is authenticated in FOB
    And the playbook "FeatureFactory" exists with workflows, activities, phases, skills, agents, and rules


  Scenario: FOB-CONTENT-BROWSER-01 Content Browser opened from Playbook detail header
    Given Maria is on the playbook detail page for "FeatureFactory"
    Then she sees a [Content Browser] button in the playbook header action bar
    And the button is positioned immediately before [Back]
    And it links to /browser/<pk>/ for that playbook
    And "Content Browser" is NOT shown in the top navigation bar


  Scenario: FOB-CONTENT-BROWSER-01b-guest-public Anonymous guest opens Content Browser for public released playbook
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development" with id=<public_pk>
    When Bob navigates to /browser/<public_pk>/
    Then the three-panel Content Browser layout renders
    And the graph canvas loads with nodes and edges for that playbook
    And the left panel heading shows "React Frontend Development"


  Scenario: FOB-CONTENT-BROWSER-01b-guest-private Anonymous guest cannot open Content Browser for private playbook
    Given Bob is not logged in
    And Mike owns a Private Released playbook with id=<private_pk>
    When Bob navigates to /browser/<private_pk>/
    Then the view returns HTTP 404
    And the Content Browser chrome is NOT rendered
    And the response does not reveal whether the playbook exists or is private


  Scenario: FOB-CONTENT-BROWSER-01c Guest Content Browser shows guest chrome and banner
    Given Bob is not logged in
    And Mike owns a Public Released playbook "React Frontend Development" with id=<public_pk>
    When Bob navigates to /browser/<public_pk>/
    Then he sees the guest banner with data-testid "guest-auth-banner"
    And the banner text includes "Sign in to create and edit playbooks"
    And he sees [Sign In] and [Register] in the guest banner
    And he does not see the full authenticated app navbar (global search, notifications, user menu)
    And he sees minimal guest chrome (brand plus auth links only)


  Scenario: FOB-CONTENT-BROWSER-02 /browser/ without a playbook id returns 404
    Given Maria navigates to /browser/
    Then the view returns HTTP 404
    And she sees the standard Django 404 page
    And the Content Browser chrome is NOT rendered


  Scenario: FOB-CONTENT-BROWSER-03 /browser/<pk>/ loads the graph for that playbook directly
    Given Maria navigates directly to /browser/3/
    Then the three-panel layout is rendered
    And the canvas loads with the graph for the playbook with id=3
    And the left panel heading shows that playbook's name
    And the structural tree is populated


  # NOTE: FOB-CONTENT-BROWSER-03b (in-browser playbook switching) REMOVED — entry is playbook-scoped from Playbook detail.
  # NOTE: FOB-CONTENT-BROWSER-03f (URL filter param normalisation) REMOVED — filter toolbar dropped.


  Scenario: FOB-CONTENT-BROWSER-03c Inaccessible or missing playbook returns 404
    # Applies to authenticated non-members and anonymous guests (Bob) alike.
    Given a visitor navigates to /browser/42/ (private playbook they cannot access)
    And a visitor navigates to /browser/9999/ (no such playbook exists)
    Then in both cases the view returns HTTP 404
    And the visitor sees the standard Django 404 page
    And the Content Browser chrome is NOT rendered
    And the response does not reveal whether the playbook exists or is private
