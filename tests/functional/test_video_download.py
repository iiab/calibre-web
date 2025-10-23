"""Video download feature tests."""

import pytest
from pytest_bdd import (
    given,
    scenario,
    then,
    when,
)

from urllib.parse import urljoin
from selenium import webdriver
import os
import time

from tests.functional.conftest import (
    find_video_by_title,
    login_if_not_logged_in,
    visit_website,
)


@pytest.fixture
def step_context():
    """Fixture to save information to use through steps."""
    return {}


@scenario("video_download.feature", "Download video 1")
def test_video_download_1():
    """Download video 1"""


@given("Calibre-Web is running and I am logged in as admin")
def _(browser, step_context):
    """Calibre-Web is running and I am logged in as admin"""
    step_context["ip_address"] = "localhost:8083"
    visit_website(browser, step_context)
    login_if_not_logged_in(browser, "Admin", "changeme")


@when("I click on 'Download to IIAB' and download the first video")
def _(browser, step_context):
    """I click on 'Download to IIA' and download the first video"""
    nature_url = "https://www.youtube.com/watch?v=mUxzKVrSAjs"
    upload = browser.find_by_id("btn-download-media")
    upload.click()
    time.sleep(1)
    browser.fill("mediaURL", nature_url)
    submit = browser.find_by_id("btn-download-media-submit")
    submit.click()


@then("I should see video 1")
def _(browser, step_context):
    """I should see video 1"""
    title_1 = "Nature | Waterfalls | Drone | Free HD Videos - No Copyright footage"
    video_1_found = find_video_by_title(browser, title_1)

    assert video_1_found, "Expected to see first video present"


@scenario("video_download.feature", "Download video 2")
def test_video_download_2():
    """Download video 2"""


@when("I click on 'Download to IIAB' and download the second video")
def _(browser, step_context):
    """I click on 'Download to IIA' and download the second video"""
    song_url = "https://www.youtube.com/watch?v=jA8C8KeuUtQ"
    upload = browser.find_by_id("btn-download-media")
    upload.click()
    time.sleep(1)
    browser.fill("mediaURL", song_url)
    submit = browser.find_by_id("btn-download-media-submit")
    submit.click()


@then("I should see video 2")
def _(browser, step_context):
    """I should see video 2"""
    # since we just added this video, it will be the last 'book'
    title_2 = "Maestro Chives, Marin Hoxha, Chris Linton - Warrior | House | NCS - Copyright Free Music"
    video_2_found = find_video_by_title(browser, title_2)

    assert video_2_found, "Expected to see second video present"
