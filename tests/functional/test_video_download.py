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


def find_video_by_href(browser, href):
    video_found = False
    count = 0
    while (not video_found) and (count <= 10):
        time.sleep(5)
        browser.reload()
        video_found = browser.is_element_present_by_xpath(f"//a[@href='{href}']", 1)
        count += 1
    return video_found


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
    url = urljoin("".join(["http://", str(step_context["ip_address"])]), "/")
    browser.visit(url)


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
    # since we just added this video, it will be the last 'book'
    book_count = len(browser.find_by_id("books_rand")) + 1
    print(book_count)
    video_1_found = find_video_by_href(browser, "/book/3")

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
    book_count = len(browser.find_by_id("books_rand")) + 1
    print(book_count)
    video_2_found = find_video_by_href(browser, "/book/4")
    book_count = len(browser.find_by_id("books_rand")) + 1
    print(book_count)

    assert video_2_found, "Expected to see second video present"
