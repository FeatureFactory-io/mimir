OUTPUT: docs/features/act-X-{entity}/{entity}-{operation}.feature

TEMPLATE:
Feature: {ScreenID} {EntityName} {Operation}
  As a {PersonaRole} ({PersonaName})
  I want to {UserGoal}
  So that {BusinessValue}

  Background:
    Given {PersonaName} is authenticated in {SystemName}
    And {InitialContext}

  Scenario: {ScenarioID} {ScenarioTitle} - Happy Path
    Given {PersonaName} is on the {ScreenName} page
    When {PersonaName} clicks the [{ButtonName}] button
    Then {PersonaName} is redirected to {TargetScreenID}

  Scenario: {ScenarioID} Search Functionality
    Given {PersonaName} is on the {ScreenName} page
    When {PersonaName} enters "{SearchTerm}" in the search box
    Then {PersonaName} sees only {EntityName} matching "{SearchTerm}"

  Scenario: {ScenarioID} Form Validation Error
    Given {PersonaName} is on the {CreateScreenID} page
    When {PersonaName} leaves "{RequiredField}" empty
    And {PersonaName} clicks [Save]
    Then {PersonaName} sees error message "{ErrorMessage}"

See .windsurf/workflows/FeatureFactory/ESM/artifacts/feature_file_template.feature for complete template with all scenario types
