Feature: Book upload
    Testing book upload

    Scenario: Upload book 1 
        Given Calibre-Web is running and I am logged in as admin
        When I click on upload and upload the first book

        Then I should see book 1

    Scenario: Upload book 2 
        Given Calibre-Web is running and I am logged in as admin
        When I click on upload and upload the second book

        Then I should see book 2
