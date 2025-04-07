Feature: Product Detail Page

  Scenario: Viewing product name and price
    Given I am on the product detail page for "Organic Cotton T-shirt"
    Then I should see the product name "Organic Cotton T-shirt"
    And I should see the product price

  Scenario: Viewing product description
    Given I am on the product detail page for "High-Performance Laptop"
    Then I should see a detailed description of the laptop's features

  Scenario: Checking product availability
    Given I am on the product detail page for "Limited Edition Sneakers"
    Then I should see the current stock availability (e.g., "In Stock," "Out of Stock")

  Scenario: Viewing product images
    Given I am on the product detail page for "Leather Handbag"
    Then I should see multiple images showcasing the handbag from different angles

  Scenario: Viewing customer reviews
    Given I am on the product detail page for "Popular Novel"
    Then I should see a section displaying customer reviews and ratings

  Scenario: Selecting product options (e.g., size, color)
    Given I am on the product detail page for "Customizable Mug"
    When I select "Blue" as the color
    And I select "12 oz" as the size
    Then the displayed product image might update to show a blue 12 oz mug
    And the price might update if options affect the cost

  Scenario: Attempting to add an out-of-stock product to the cart
    Given I am on the product detail page for an "Out of Stock" item
    When I click the "Add to Cart" button
    Then I should see a message indicating that the product is out of stock
    And the product should not be added to my shopping cart