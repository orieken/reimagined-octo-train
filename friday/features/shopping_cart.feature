Feature: Shopping Cart

  Scenario: Adding a product to the cart
    Given I am on the product detail page for "Eco-Friendly Water Bottle"
    When I click the "Add to Cart" button
    Then the "Shopping Cart" icon should display "1" item
    And I should see a notification that the product has been added to the cart

  Scenario: Viewing items in the cart
    Given I have added "Eco-Friendly Water Bottle" to my cart
    When I navigate to the "Shopping Cart" page
    Then I should see "Eco-Friendly Water Bottle" listed in my cart
    And I should see the quantity, price per item, and subtotal

  Scenario: Increasing the quantity of an item in the cart
    Given I have one "Eco-Friendly Water Bottle" in my cart
    When I increase the quantity to "2"
    Then the quantity of "Eco-Friendly Water Bottle" in my cart should be "2"
    And the cart subtotal should be updated accordingly

  Scenario: Decreasing the quantity of an item in the cart
    Given I have two "Eco-Friendly Water Bottles" in my cart
    When I decrease the quantity to "1"
    Then the quantity of "Eco-Friendly Water Bottle" in my cart should be "1"
    And the cart subtotal should be updated accordingly

  Scenario: Removing an item from the cart
    Given I have "Eco-Friendly Water Bottle" and "Reusable Shopping Bag" in my cart
    When I click the "Remove" button next to "Reusable Shopping Bag"
    Then "Reusable Shopping Bag" should be removed from my cart
    And the cart subtotal should be updated

  Scenario: Applying a discount code to the cart
    Given I have items in my cart
    When I enter a valid discount code "SUMMER20" in the discount code field
    And I click "Apply"
    Then a discount should be applied to my order total
    And I should see the discounted price

  Scenario: Attempting to apply an invalid discount code
    Given I have items in my cart
    When I enter an invalid discount code "INVALIDCODE" in the discount code field
    And I click "Apply"
    Then I should see an error message indicating the code is invalid
    And no discount should be applied

  Scenario: Proceeding to checkout from the cart
    Given I have items in my cart
    When I click the "Proceed to Checkout" button
    Then I should be redirected to the checkout page