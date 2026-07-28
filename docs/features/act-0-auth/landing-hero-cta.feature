@landing @auth
Feature: FOB-LANDING-CTA Landing Hero Primary Action
  As a visitor or signed-in user on the Mimir landing page
  I want a clear primary hero action with a matching icon
  So that I know whether to register or connect my IDE via MCP

  Background:
    Given Bob is on the FOB landing page at "/"


  Scenario: LANDING-CTA-01 Guest hero shows Register button with icon
    Given Bob is not logged in
    Then he sees [Register] with data-testid "landing-cta-register"
    And the Register hero button includes the same user-plus icon as the navbar Register link
    And he does not see [Connect MCP] with data-testid "landing-cta-connect-mcp"


  Scenario: LANDING-CTA-02 Authenticated hero shows Connect MCP primary button with icon
    Given Maria is authenticated in FOB
    When Maria is on the FOB landing page at "/"
    Then she sees [Connect MCP] with data-testid "landing-cta-connect-mcp"
    And the Connect MCP hero button uses the primary action style
    And the Connect MCP hero button includes a plug icon
    And she does not see [Register] with data-testid "landing-cta-register"
    When she clicks [Connect MCP]
    Then the page scroll target is the MCP configuration section with data-testid "landing-mcp-connect"
