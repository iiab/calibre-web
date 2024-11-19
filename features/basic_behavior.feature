Feature: Basic behavior 
    Testing basic behavior like showing home page and login 

    Scenario: Home Page 
        Given Calibre web is running 
        When I go to the home page 

        Then I should not see the error message
        And see homepage information

    Scenario: Login 
        Given I visit the calibre web homepage 
        When I login with valid credentials

        Then I should see the success message
        And see the information for logged users 


