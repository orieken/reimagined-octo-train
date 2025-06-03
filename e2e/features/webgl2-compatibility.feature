@webgl2 @focus
Feature: WebGL2 Compatibility Check
  As a user
  I want to check if my browser supports WebGL2
  So that I can use WebGL2-based applications

  Scenario: Check WebGL2 compatibility on get.webgl.org
    Given I navigate to the WebGL2 test site
    Then I should see if WebGL2 is supported
    And I should see the WebGL2 support message

  Scenario: Check WebGL2 compatibility on webglreport.com
    Given I navigate to the WebGL Report site
    Then I should see if WebGL2 is supported on the report
    And I should see detailed WebGL2 information
    And I should see the WebGL2 version
    And I should see the renderer information
    And I should see the vendor information
