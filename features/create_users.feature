Feature: Create User
  Testing create User


  Scenario Outline: Create users
      Given Calibre-Web is running and I am logged in as admin
      When I click on Admin button and create user with <username>, <password>, and <email>
      Then I should see that <username> is created

      Examples:
      | username | password  | email         |
      | chloe    | Chloe123! | chloe@iiab.io |
      | ella     | Ella123!  | ella@iiab.io  |
