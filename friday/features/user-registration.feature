Feature: User Registration

  Scenario: Successful user registration
    Given I am on the registration page
    When I enter a unique email "newuser@example.com"
    And I enter a password "password123"
    And I confirm the password "password123"
    And I click the "Register" button
    Then I should be redirected to my account dashboard
    And I should see a success message

  Scenario: Attempting to register with an existing email
    Given I am on the registration page
    When I enter an already registered email "existinguser@example.com"
    And I enter a password "anotherpassword"
    And I confirm the password "anotherpassword"
    And I click the "Register" button
    Then I should see an error message indicating that the email is already in use

  Scenario: Password mismatch during registration
    Given I am on the registration page
    When I enter an email "testuser@example.com"
    And I enter a password "secure1"
    And I enter a different password "secure2" in the confirm password field
    And I click the "Register" button
    Then I should see an error message indicating that the passwords do not match

Feature: User Login

  Scenario: Successful user login
    Given I am on the login page
    When I enter my registered email "existinguser@example.com"
    And I enter my correct password "correctpassword"
    And I click the "Login" button
    Then I should be redirected to my account dashboard
    And I should see a personalized greeting

  Scenario: Attempting to login with an incorrect password
    Given I am on the login page
    When I enter my registered email "existinguser@example.com"
    And I enter an incorrect password "wrongpassword"
    And I click the "Login" button
    Then I should see an error message indicating invalid credentials

  Scenario: Attempting to login with an unregistered email
    Given I am on the login page
    When I enter an unregistered email "nonexistent@example.com"
    And I enter any password
    And I click the "Login" button
    Then I should see an error message indicating invalid credentials