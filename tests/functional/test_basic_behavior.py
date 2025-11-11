"""Basic behavior feature tests."""

import pytest
from pytest_bdd import (
    given,
    scenario,
    then,
    when,
)

from urllib.parse import urljoin
from selenium import webdriver
from tests.functional.conftest import (
    login_if_not_logged_in,
    login_with_username_and_password,
    visit_website,
)


@scenario("basic_behavior.feature", "Home Page")
def test_home_page():
    """Home Page."""


@given("Calibre-Web is running")
def _(step_context):
    """Calibre-Web is running."""


@when("I go to the home page")
def _(browser, step_context):
    """I go to the home page."""
    visit_website(browser, step_context)


@then("I should not see the error message")
def _(browser, step_context):
    """I should not see the error message."""


@then("see homepage information")
def _(browser):
    """see homepage information."""
    assert browser.is_text_present("Books"), "Page successfully loaded!"


@scenario("basic_behavior.feature", "Login")
def test_login():
    """Login."""


@given("I visit the Calibre-Web homepage")
def _(browser, step_context):
    """I visit the Calibre-Web homepage."""
    visit_website(browser, step_context)


@when("I login with valid credentials")
def _(browser, step_context):
    """I login with valid credentials."""
    login_with_username_and_password(browser, "Admin", "changeme")


@then("I should see the success message")
def _(browser, step_context):
    """I should see the success message."""
    assert browser.is_text_present("You are now logged in as:"), "Login successful"


@then("see the information for logged users")
def _(browser):
    """see the information for logged users"""
    assert browser.is_text_present("Books"), (
        'Expected "Books" text to be visible on the home page'
    )
    assert browser.is_text_present("Download to IIAB"), (
        'Expected "Download to IIAB" button for logged users'
    )
