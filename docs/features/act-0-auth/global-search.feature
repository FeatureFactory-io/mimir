Feature: FOB-GLOBAL-SEARCH Global search and search results (NAV-06)
  As a methodology author (Maria)
  I want to search across all playbook contents from the navbar and refine on a results page
  So that I can quickly find and open playbooks, workflows, activities, and related entities

  # Results page (All types): Bootstrap accordion sections — first expanded, single open panel.
  # Highlight: case-insensitive <mark class="mm-search-highlight"> in title, context, snippet, suggestions.
  # Mockup: /mockups/search/?q=React (DEBUG only)

  Background:
    Given Maria is authenticated in FOB
    And she has access to playbooks she owns plus public non-draft playbooks from other authors

  # ── Navbar → results page flow ───────────────────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-01 Navbar search submits to results with query pre-filled
    Given Maria is on any FOB screen with the navbar visible
    When she types "React" in the global search input with data-testid "global-search-input"
    And she submits the global search form with data-testid "global-search-form"
    Then she is on FOB Search Results at "/search/?q=React"
    And the Search for field with data-testid "global-search-query-input" has value "React"
    And she does not see a Status filter on the search results page
    And she does not see a Source filter on the search results page

  Scenario: FOB-GLOBAL-SEARCH-02 See all results link preserves navbar query
    Given Maria has typed "React" in the navbar global search input
    And live suggestions are visible with data-testid "global-search-suggestions"
    When she clicks "See all results" in the suggestions dropdown
    Then she is on "/search/?q=React"
    And the Search for field with data-testid "global-search-query-input" has value "React"

  # ── Results page filter bar ───────────────────────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-03 Results page filter bar has Search for and Type only
    Given Maria is on FOB Search Results at "/search/?q=React"
    Then she sees the page root with data-testid "global-search-results-page"
    And she sees the filter form with data-testid "global-search-filters-form"
    And she sees the Search for input with data-testid "global-search-query-input"
    And she sees the Type dropdown with data-testid "global-search-type-filter"
    And she sees the [Search] button with data-testid "global-search-submit-button"
    And she does not see an element with data-testid "filter-status"
    And she does not see an element with data-testid "filter-source"

  Scenario: FOB-GLOBAL-SEARCH-04 Refine query on the results page
    Given Maria is on FOB Search Results at "/search/?q=React"
    When she clears the Search for field
    And she enters "Component" in the Search for field with data-testid "global-search-query-input"
    And she clicks [Search] with data-testid "global-search-submit-button"
    Then she is on "/search/?q=Component"
    And the summary line shows results for "Component"

  Scenario: FOB-GLOBAL-SEARCH-05 Type filter options cover all playbook entity types
    Given Maria is on FOB Search Results at "/search/?q=React"
    When she opens the Type dropdown with data-testid "global-search-type-filter"
    Then she sees type options:
      | value      | label      |
      |            | All types  |
      | playbooks  | Playbooks  |
      | workflows  | Workflows  |
      | phases     | Phases     |
      | activities | Activities |
      | artifacts  | Artifacts  |
      | skills     | Skills     |
      | agents     | Agents     |
      | rules      | Rules      |

  Scenario: FOB-GLOBAL-SEARCH-06 Type filter narrows results to one flat entity section
    Given Maria is on FOB Search Results at "/search/?q=React"
    When she selects "Skills" from the Type dropdown
    And she clicks [Search] with data-testid "global-search-submit-button"
    Then she is on "/search/?q=React&type=skills"
    And she sees the Skills results section with data-testid "global-search-skills"
    And she does not see the Playbooks results section with data-testid "global-search-playbooks"
    And she does not see the Workflows results section with data-testid "global-search-workflows"
    And she does not see an accordion with id "global-search-sections"

  # ── Grouped results (All types) ───────────────────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-07 All types view shows summary and grouped accordion sections
    Given Maria is on FOB Search Results at "/search/?q=React"
    And matching entities exist across multiple types
    Then she sees the summary with data-testid "global-search-summary"
    And the summary text matches "Showing results for \"React\""
    And she sees an accordion with id "global-search-sections"
    And she sees grouped sections in order:
      | section    | data-testid                 | toggle data-testid                    |
      | Playbooks  | global-search-playbooks     | global-search-section-toggle-playbooks |
      | Workflows  | global-search-workflows     | global-search-section-toggle-workflows |
      | Phases     | global-search-phases        | global-search-section-toggle-phases    |
      | Activities | global-search-activities    | global-search-section-toggle-activities |
      | Artifacts  | global-search-artifacts     | global-search-section-toggle-artifacts |
      | Skills     | global-search-skills        | global-search-section-toggle-skills    |
      | Agents     | global-search-agents        | global-search-section-toggle-agents    |
      | Rules      | global-search-rules         | global-search-section-toggle-rules     |

  Scenario: FOB-GLOBAL-SEARCH-08 All types view hides sections with zero matches
    Given Maria is on FOB Search Results at "/search/?q=React"
    And no Rules match "React"
    Then she does not see the Rules results section with data-testid "global-search-rules"
    And other sections with matches remain visible

  Scenario: FOB-GLOBAL-SEARCH-09 Each result row shows title context snippet and type badge
    Given Maria is on FOB Search Results at "/search/?q=React"
    And "React Frontend Development" is a matching playbook
    Then she sees a result row with data-testid "global-search-result-playbook-1"
    And the row shows title "React Frontend Development"
    And the row shows context "Mike Chen · v1.2 · Development"
    And the row shows a text snippet from the matched field
    And the row shows a type badge "Playbook"
    And matching occurrences of "React" in title, context, and snippet are wrapped in mark.mm-search-highlight

  Scenario: FOB-GLOBAL-SEARCH-09b Search term highlight is case-insensitive
    Given Maria is on FOB Search Results at "/search/?q=react"
    And a playbook title contains "React Frontend Development"
    Then the title shows mark.mm-search-highlight around "React" despite lowercase query

  Scenario: FOB-GLOBAL-SEARCH-09c Highlight styling uses design token yellow background
    Given Maria is on FOB Search Results at "/search/?q=React"
    And a result row contains a highlighted match
    Then mark.mm-search-highlight elements use background-color var(--hg-yellow)
    And highlighted text inherits the surrounding font colour

  Scenario: FOB-GLOBAL-SEARCH-10 Activity result shows playbook and workflow breadcrumb
    Given Maria is on FOB Search Results at "/search/?q=React"
    And "Setup React Project" is a matching activity
    Then she sees a result row with data-testid "global-search-result-activity-20"
    And the row shows context "React Frontend Development › Component Development"

  Scenario: FOB-GLOBAL-SEARCH-11 Clicking a result navigates to entity detail
    Given Maria is on FOB Search Results at "/search/?q=React"
    When she clicks the result link for "React Frontend Development"
    Then she is redirected to that playbook's detail page

  # ── Empty and no-query states ─────────────────────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-12 Empty state when query has no matches
    Given Maria is on FOB Search Results at "/search/?q=zzzznomatch"
    Then she sees the empty state with data-testid "global-search-empty-state"
    And the empty state message includes "No results found"
    And the empty state suggests broadening the query or switching Type to All types

  Scenario: FOB-GLOBAL-SEARCH-13 No query shows prompt without empty-state error
    Given Maria opens FOB Search Results at "/search/" without a query parameter
    Then she does not see the empty state with data-testid "global-search-empty-state"
    And she sees a prompt to enter a search term with data-testid "global-search-no-query-prompt"

  # ── Navbar live suggestions ───────────────────────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-14 Live suggestions show top hits per entity type
    Given Maria is on any FOB screen with the navbar visible
    When she types "React" in the global search input with data-testid "global-search-input"
    Then she sees suggestions with data-testid "global-search-suggestions"
    And suggestions include up to 5 rows per entity type that has matches
    And suggestions may include Playbooks, Workflows, Activities, Skills, Artifacts, Agents, Rules, and Phases
    And each suggestion row links to the entity detail page

  Scenario: FOB-GLOBAL-SEARCH-15 Suggestions omit entity types with no matches
    Given Maria is on any FOB screen with the navbar visible
    When she types "React" in the global search input
    And no Rules match "React"
    Then the suggestions dropdown does not include a Rules section

  Scenario: FOB-GLOBAL-SEARCH-16 Empty query returns no suggestions fragment
    Given Maria is on any FOB screen with the navbar visible
    When she clears the global search input
    Then the suggestions container with id "global-search-suggestions-container" is empty

  # ── Access scope ──────────────────────────────────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-17 Search excludes draft playbooks Maria cannot read
    Given another author has a draft public playbook "Secret Draft"
    And Maria is not the author of "Secret Draft"
    When Maria searches for "Secret Draft"
    Then "Secret Draft" does not appear in her search results

  Scenario: FOB-GLOBAL-SEARCH-18 Anonymous users do not see navbar global search
    Given Bob is not authenticated
    When he views any public FOB page
    Then he does not see the global search form with data-testid "global-search-form"

  # ── Accordion expand / collapse (All types) ───────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-19 All types view first section expanded others collapsed
    Given Maria is on FOB Search Results at "/search/?q=React"
    And matching entities exist in Playbooks and Workflows sections
    Then the Playbooks section toggle has aria-expanded "true"
    And the Playbooks collapse panel has class "show"
    And the Workflows section toggle has aria-expanded "false"
    And the Workflows collapse panel does not have class "show"

  Scenario: FOB-GLOBAL-SEARCH-20 Maria expands a collapsed section
    Given Maria is on FOB Search Results at "/search/?q=React"
    And the Workflows section is collapsed
    When she clicks the Workflows section toggle with data-testid "global-search-section-toggle-workflows"
    Then the Workflows section toggle has aria-expanded "true"
    And the Workflows result rows become visible
    And the Workflows section chevron indicates expanded state

  Scenario: FOB-GLOBAL-SEARCH-21 Expanding one section collapses the previously open section
    Given Maria is on FOB Search Results at "/search/?q=React"
    And the Playbooks section is expanded
    When she clicks the Workflows section toggle with data-testid "global-search-section-toggle-workflows"
    Then the Workflows section is expanded
    And the Playbooks section is collapsed
    # Bootstrap accordion data-bs-parent="#global-search-sections" — single open panel

  Scenario: FOB-GLOBAL-SEARCH-22 Maria collapses the open section
    Given Maria is on FOB Search Results at "/search/?q=React"
    And the Playbooks section is expanded
    When she clicks the Playbooks section toggle again
    Then the Playbooks section toggle has aria-expanded "false"
    And the Playbooks result rows are hidden

  Scenario: FOB-GLOBAL-SEARCH-23 Single type filter renders flat list without accordion
    Given Maria is on FOB Search Results at "/search/?q=React&type=skills"
    Then she does not see an accordion with id "global-search-sections"
    And she sees the Skills section as a flat card with data-testid "global-search-skills"
    And the Skills section does not have a collapse toggle

  Scenario: FOB-GLOBAL-SEARCH-24 Section headers show icon label and count badge
    Given Maria is on FOB Search Results at "/search/?q=React"
    And the Playbooks section has 2 matches
    Then the Playbooks section header shows icon fa-book-sparkles
    And the header shows label "Playbooks"
    And the header shows count badge "2"

  # ── Search term highlighting in suggestions ───────────────────────────────

  Scenario: FOB-GLOBAL-SEARCH-25 Navbar suggestions highlight query in title and context
    Given Maria is on any FOB screen with the navbar visible
    When she types "React" in the global search input with data-testid "global-search-input"
    Then she sees suggestions with data-testid "global-search-suggestions"
    And suggestion rows wrap matching "React" in mark.mm-search-highlight in title and context
