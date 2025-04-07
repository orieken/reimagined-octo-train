Feature: Customer Support - Contact Form

  Scenario: Submitting a contact form with valid details
        Given I am on the "Contact Us" page
        When I enter my name "Alice Smith"
        And I enter my email "alice.smith@example.com"
        And I enter a subject "Order Inquiry"
        And I enter a message "I have a question about my recent order."
        And I click the "Submit" button
        Then I should see a confirmation message indicating that my message has been sent
        And the website should attempt to send an email to customer support

      Scenario: Attempting to submit a contact form with a missing email
        Given I am on the "Contact Us" page
        When I enter my name "Bob Johnson"
        And I leave the email field blank
        And I enter a subject "General Question"
        And I enter a message "This is a general inquiry."
        And I click the "Submit" button
        Then I should see an error message indicating that the email field is required

      Scenario: Attempting to submit a contact form with an invalid email format
        Given I am on the "Contact Us" page
        When I enter my name "Charlie Brown"
        And I enter an invalid email "charlie.brown"
        And I enter a subject "Website Issue"
        And I enter a message "I am experiencing a problem with the website."
        And I click the "Submit" button
        Then I should see an error message indicating that the email format is invalid

    Feature: Customer Support - FAQ

      Scenario: Viewing the FAQ page
        Given I am on any page
        When I navigate to the "FAQ" page
        Then I should see a list of frequently asked questions and their answers

      Scenario: Expanding an answer to a question
        Given I am on the "FAQ" page
        When I click on the question "What is your return policy?"
        Then the answer to "What is your return policy?" should be displayed

      Scenario: Searching for a keyword in the FAQ
        Given I am on the "FAQ" page
        When I enter "shipping" in the FAQ search bar
        And I click the search button
        Then I should see a list of FAQ items related to "shipping"
