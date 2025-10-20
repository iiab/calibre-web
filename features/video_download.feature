Feature: Video download
    Testing video download

    Scenario: Download video 1 
        Given Calibre-Web is running and I am logged in as admin
        When I click on 'Download to IIAB' and download the first video

        Then I should see video 1

    Scenario: Download video 2 
        Given Calibre-Web is running and I am logged in as admin
        When I click on 'Download to IIAB' and download the second video

        Then I should see video 2
