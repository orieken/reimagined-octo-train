Feature: Product Browsing

  Scenario: Viewing all products on the homepage
    Given I am on the homepage
    When I navigate to the "Products" section
    Then I should see a list of products

  Scenario: Filtering products by category
    Given I am on the "Products" page
    When I select the "Electronics" category filter
    Then I should only see products belonging to the "Electronics" category

  Scenario: Sorting products by price (low to high)
    Given I am on the "Products" page
    When I select "Price: Low to High" from the sort options
    Then the products should be displayed in ascending order of price

  Scenario: Searching for a product by name
    Given I am on any page
    When I enter "coffee maker" in the search bar
    And I click the search button
    Then I should see search results containing "coffee maker"

  Scenario: Viewing product details
    Given I am on the "Products" page
    When I click on a product named "Wireless Headphones"
    Then I should be redirected to the product details page for "Wireless Headphones"
    And I should see the product name, description, and price

  Scenario: Applying multiple filters
    Given I am on the "Products" page
    When I select the "Electronics" category filter
    And I select the "Brand: Sony" filter
    Then I should only see "Sony" brand products within the "Electronics" category

  Scenario: Clearing applied filters
    Given I have applied filters for "Electronics" and "Brand: Sony" on the "Products" page
    When I click the "Clear Filters" button
    Then all filters should be removed
    And I should see products from all categories and brands