Feature: Calibre-Web 
    Web app for browsing, reading and downloading ebooks. 

    Scenario: Calibre web website should be available 
        Given IIAB is running 
        When I go to the calibre-web path 

        Then I should not see the error message
        And shows the calibre-web homepage 
