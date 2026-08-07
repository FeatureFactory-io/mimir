@wip @experts @karma
Feature: FOB-EXPERTS-LIST+FIND-1 Experts Leaderboard
  As a competency center head (Elena)
  I want to browse top contributors by methodology category
  So that I can discover experts to invite to a guild or RFP team

  Background:
    Given Elena is authenticated in FOB
    And the following experts exist with Karma and primary categories:
      | username | display_name      | total_karma | primary_category | expertise_hint_prefix                    |
      | mchen    | Mike Chen         |       12450 | Development      | 2 released playbooks · specializes in    |
      | mrodriguez | Maria Rodriguez |        8200 | Design           | Accessibility-focused contributor to     |
      | jlee     | Jordan Lee        |        6100 | Development      | 1 released playbook · PIP contributor    |
      | apatel   | Alex Patel        |        5400 | Product          | Product discovery frameworks             |
      | skim     | Sam Kim           |        4800 | Research         | UX research methodology author           |

  # ── Navigation ────────────────────────────────────────────────────────────

  Scenario: EXPERTS-LIST-01 Access Experts from top navigation
    Given Elena is anywhere in FOB
    When she clicks "Experts" in the top navigation bar
    Then she is redirected to /experts/
    And the page title reads "Experts"
    And data-testid="experts-leaderboard" is present
    And the subtitle reads "Top contributors by methodology category"

  # ── Category tabs ─────────────────────────────────────────────────────────

  Scenario: EXPERTS-LIST-02 Category pill tabs filter the leaderboard
    Given Elena is on FOB-EXPERTS-LIST+FIND-1
    Then data-testid="experts-category-tabs" shows pills:
      | category    |
      | Product     |
      | Development |
      | Research    |
      | Design      |
      | Other       |
    When she selects the "Development" tab
    Then the active tab is "Development"
    And the browser console logs "[experts] category tab: development"

  Scenario: EXPERTS-LIST-03 Development tab shows top experts by primary category
    Given Elena is on /experts/?category=development
    Then the leaderboard shows at most 5 cards
    And each card has primary category badge "Development"
    And cards are ordered by total Karma descending:
      | rank | display_name |
      |    1 | Mike Chen    |
      |    2 | Jordan Lee   |

  Scenario: EXPERTS-LIST-04 Each card shows rank, avatar, name, Karma, badge, and hint
    Given Elena is on /experts/?category=development
    Then the card for "Mike Chen" (data-testid="experts-card-mchen") displays:
      | field            | value                                              |
      | Rank             | 1                                                  |
      | Display name     | Mike Chen                                          |
      | Total Karma      | 12,450                                             |
      | Primary category | Development                                        |
      | Expertise hint   | truncated contribution summary or numeric fallback |
    And an avatar or initials element is visible for "Mike Chen"

  Scenario: EXPERTS-LIST-05 View profile links to public expert detail
    Given Elena is on /experts/?category=development
    When she clicks [View profile] on the card for "Mike Chen"
    Then she is redirected to FOB-EXPERT-VIEW-1 at /experts/mchen/

  Scenario: EXPERTS-LIST-06 Empty category tab shows encouragement message
    Given no expert has primary category "Other"
    When Elena selects the "Other" tab on /experts/
    Then she sees empty state text "No experts in Other yet — release a playbook to be the first"
    And data-testid="experts-leaderboard" shows zero cards

  # ── Guest access ──────────────────────────────────────────────────────────

  Scenario: EXPERTS-LIST-07 Guest sees read-only leaderboard without profile Karma
    Given Bob is not logged in
    When Bob GET "/experts/"
    Then he sees data-testid="experts-leaderboard"
    And he sees data-testid="guest-auth-banner"
    And the guest banner includes a [Register] link
    And he does not see data-testid="profile-karma-card"
