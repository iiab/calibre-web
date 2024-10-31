"""Calibre-Web feature tests."""
import pytest
from pytest_bdd import (
    given,
    scenario,
    then,
    when,
)

import subprocess 
from urllib.parse import urljoin
import time

@pytest.fixture(scope='session')
def splinter_headless():
    """Override splinter headless option."""
    return True

@pytest.fixture(scope='session')
def splinter_webdriver():
    """Override splinter webdriver name."""
    return 'chrome'

# Fixture to save information to use through steps
@pytest.fixture
def step_context():
    return {}

@scenario('iiab/calibre-web.feature', 'Calibre web website should be available')
def test_calibre_web_website_should_be_available():
    """Calibre web website should be available."""

@given('IIAB is running')
def _(step_context):
    """IIAB is running."""
    # Extract IP address from Multipass 
    result = subprocess.run(['multipass', 'exec', 'box', '--', 'hostname', '-I'], capture_output=True, text=True)
    ip_address = str(result.stdout).strip("\r\n ")
    step_context['ip_address'] = ip_address

@when('I go to the calibre-web path')
def navigate_to_calibre(browser, step_context):
    """I go to the calibre-web path."""
    url = urljoin("".join(['http://', str(step_context['ip_address'])]), '/books')
    browser.visit(url)

@then('I should not see the error message')
def _(step_context):
    """I should not see the error message."""
    #raise NotImplementedError


@then('shows the calibre-web homepage')
def calibre_web_homepage(browser):
    """shows the calibre-web homepage."""
    print("!!!!!!!")
    print(browser.title)
    print(browser.url)
    print("!!!!!!!")
    assert browser.is_text_present('Books'), 'Book test'
 

