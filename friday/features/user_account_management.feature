Feature: User Account - Profile Information

  Scenario: Viewing profile information
    Given I am logged in
    When I navigate to the "Profile Information" section
    Then I should see my name, email address, and phone number (if provided)

  Scenario: Updating profile name
    Given I am on the "Edit Profile" page
    When I change my first name to "Jane"
    And I click "Save Changes"
    Then my displayed first name should be updated to "Jane"
    And I should see a success message

Feature: User Account - Address Book

  Scenario: Adding a new shipping address
    Given I am on the "Address Book" page
    When I click "Add New Address"
    And I enter a new address "456 Oak Ave, Anytown, CA 90211"
    And I click "Save Address"
    Then the new address should be listed in my address book

  Scenario: Setting a default shipping address
    Given I have multiple addresses in my address book
    When I click the "Set as Default" button next to an address
    Then that address should be marked as my default shipping address

Feature: User Account - Payment Methods

  Scenario: Adding a new payment method
    Given I am on the "Payment Methods" page
    When I click "Add New Payment Method"
    And I enter valid credit card details
    And I click "Save Payment Method"
    Then the new payment method should be listed in my saved payment methods