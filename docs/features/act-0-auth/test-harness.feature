@harness
Feature: AT-HARNESS Django-client acceptance execution
  The test harness must execute real application requests without a browser.

  Scenario: AT-HARNESS-01 Check the real health endpoint
    Given an anonymous AT visitor
    When the AT visitor requests "/health/"
    Then the AT response status is 200
