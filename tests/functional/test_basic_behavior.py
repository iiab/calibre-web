"""Basic behavior feature tests."""
import pytest
from pytest_bdd import (
    given,
    scenario,
    then,
    when,
)

import os
import subprocess
from urllib.parse import urljoin
import time

@pytest.fixture(scope='session')
def splinter_headless():
    """Override splinter headless option."""
    if os.environ['HEADLESS'] == "true":
        return True
    else:
        return False

@pytest.fixture
def step_context():
    """Fixture to save information to use through steps."""
    return {}

@scenario('basic_behavior.feature', 'Home Page')
def test_home_page():
    """Home Page."""


@given('Calibre web is running')
def _(step_context):
    """Calibre web is running."""
    step_context['ip_address'] = 'localhost:8083'


@when('I go to the home page')
def _(browser, step_context):
    """I go to the home page."""
    url = urljoin("".join(['http://', str(step_context['ip_address'])]), '/')
    browser.visit(url)


@then('I should not see the error message')
def _(browser, step_context):
    """I should not see the error message."""

@then('see homepage information')
def _(browser):
    """see homepage information."""
    print("!!!!!!!")
    print(browser.title)
    print(browser.url)
    print("!!!!!!!")
    assert browser.is_text_present('Books'), 'Book test'

@scenario('basic_behavior.feature', 'Login')
def test_login():
    """Login."""


@given('I visit the calibre web homepage')
def _(browser, step_context):
    """I visit the calibre web homepage."""
    step_context['ip_address'] = 'localhost:8083'
    url = urljoin("".join(['http://', str(step_context['ip_address'])]), '/')
    browser.visit(url)


@when('I login with valid credentials')
def _(browser, step_context):
    """I login with valid credentials."""
    guest = browser.find_by_id('top_user')
    guest.click()
    browser.fill('username', 'Admin')
    browser.fill('password', 'changeme')
    button = browser.find_by_name('submit')
    # Interact with elements
    button.click()


@then('I should see the success message')
def _(browser, step_context):
    """I should see the success message."""
    assert browser.is_text_present('You are now logged in as:'), 'Login successful'

@then('see the information for logged users')
def _(browser):
    """see the information for logged users"""
    assert browser.is_text_present('Books'), 'Expected "Books" text to be visible on the home page'
    assert browser.is_text_present('Download to IIAB'), 'Expected "Download to IIAB" button for logged users'
