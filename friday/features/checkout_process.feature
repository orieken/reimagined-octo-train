Feature: Checkout Process - Shipping Information

  Scenario: Proceeding to shipping information as a logged-in user
    Given I am logged in and have items in my cart
    When I proceed to checkout
    Then I should be on the shipping information page
    And my default shipping address should be pre-filled (if available)

  Scenario: Entering new shipping address
    Given I am on the shipping information page
    When I enter my name "John Doe"
    And I enter my address "123 Main St"
    And I enter my city "Anytown"
    And I select "California" as the state
    And I enter my zip code "90210"
    And I click "Continue to Payment"
    Then my entered shipping information should be saved for this order

Feature: Checkout Process - Payment Method

  Scenario: Selecting a payment method
    Given I have entered my shipping information
    When I proceed to the payment method page
    Then I should see a list of available payment methods (e.g., Credit Card, PayPal)
    When I select "Credit Card"
    Then I should see fields to enter my credit card details

  Scenario: Entering valid credit card details
    Given I have selected "Credit Card" as my payment method
    When I enter a valid card number "1234567890123456"
    And I enter the expiry date "12/25"
    And I enter the CVV "123"
    And I click "Place Order"
    Then my order should be successfully placed (assuming other validations pass)

Feature: Checkout Process - Order Confirmation

  Scenario: Viewing order confirmation
    Given I have successfully placed an order
    Then I should be redirected to the order confirmation page
    And I should see my order number
    And I should see a summary of the items ordered
    And I should see the shipping address and billing information

  Scenario: Receiving an order confirmation email
    Given I have successfully placed an order
    Then I should receive an order confirmation email at my registered email address
    And the email should contain my order details
