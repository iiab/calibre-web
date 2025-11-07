Feature: Create User
  Testing create User


  Scenario: Create user 1
      Given Calibre-Web is running and I am logged in as admin
      When I click on Admin button and create user 1

      Then I should see that user 1 is created

  Scenario: Create user 2
      Given Calibre-Web is running and I am logged in as admin
      When I click on Admin button and create user 2

      Then I should see that user 2 is created
