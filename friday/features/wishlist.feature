Feature: Product Reviews

  Scenario: Viewing existing product reviews
    Given I am on the product detail page for "Electric Kettle"
    Then I should see a section displaying customer reviews and their ratings

  Scenario: Submitting a product review as a logged-in user
    Given I am logged in and on the product detail page for "Travel Backpack"
    When I enter a review text "Great backpack for travel!"
    And I select a rating of 5 stars
    And I click "Submit Review"
    Then my review should be displayed on the product detail page
    And my username should be associated with the review

  Scenario: Attempting to submit a review without a rating
    Given I am logged in and on the product detail page for a product
    When I enter a review text
    And I do not select a rating
    And I click "Submit Review"
    Then I should see an error message asking me to provide a rating

  Scenario: Viewing the average product rating
    Given I am on the product detail page for a product with multiple reviews
    Then I should see the average rating displayed (e.g., 4.5 out of 5 stars)

  Scenario: Filtering reviews by rating
    Given I am on the product detail page with multiple reviews
    When I select to filter reviews by "5 stars"
    Then I should only see reviews with a 5-star rating