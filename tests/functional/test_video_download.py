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


@pytest.fixture
def step_context():
    """Fixture to save information to use through steps."""
    return {}


@scenario("video_download.feature", "Download video 1")
def test_upload_book_1():
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
    browser.fill("mediaURL", nature_url)
    submit = browser.find_by_id("btn-download-media-submit")
    submit.click()


@then("I should see video 1")

