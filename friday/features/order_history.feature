Feature: Order History

  Scenario: Viewing order history as a logged-in user
    Given I am logged in
    When I navigate to the "Order History" page
    Then I should see a list of my past orders
    And each order should display the order number, date, and status

  Scenario: Viewing details of a specific order
    Given I am on the "Order History" page
    When I click on an order with number "12345"
    Then I should see the details of order "12345"
    Including the items ordered, quantities, prices, shipping address, and tracking information (if available)

  Scenario: Checking the shipping status of an order
    Given I am viewing the details of an order that has been shipped
    Then I should see the current shipping status (e.g., "Shipped," "Out for Delivery," "Delivered")
    And I should see a tracking number or link to track the shipment

  Scenario: Reordering a previously placed order
    Given I am viewing the details of a completed order
    When I click the "Reorder" button
    Then all the items from that order should be added to my shopping cart

  Scenario: Filtering order history by date range
    Given I am on the "Order History" page
    When I select a start date "01/01/2025" and an end date "03/31/2025"
    And I click "Apply Filter"
    Then I should only see orders placed within that date range