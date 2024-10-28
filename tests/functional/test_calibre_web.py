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
#from selenium import webdriver
#from webdriver_manager.chrome import ChromeDriverManager
#from webdriver_manager.firefox import GeckoDriverManager
#from selenium.webdriver.chrome.service import Service as ChromiumService
#from webdriver_manager.core.os_manager import ChromeType
#from selenium.webdriver.firefox.service import Service as FirefoxService

#from selenium.webdriver.common.selenium_manager import SeleniumManager

@pytest.fixture(scope='session')
def splinter_headless():
    """Override splinter headless option."""
    return True 

@pytest.fixture(scope='session')
def splinter_webdriver():
    """Override splinter webdriver name."""
    return 'chrome'

@scenario('iiab/calibre-web.feature', 'Calibre web website should be available')
def test_calibre_web_website_should_be_availabile():
    """Calibre web website should be available."""

@given('IIAB is running')
def _():
    """IIAB is running."""
    result = subprocess.run(['multipass', 'info', 'box'], capture_output=True, text=True)
    print("*****")
    print(result.stdout)
    print("*****")
    #os.system("multipass info box")

@when('I go to the calibre-web path')
def navigate_to_calibre(browser):
    """I go to the calibre-web path."""
    # Extract IP address from Multipass 
    url = urljoin('http://10.26.33.118', '/books')
    print("////")
    print(url)
    print("////")
    browser.visit(url)


@then('I should not see the error message')
def _():
    """I should not see the error message."""
    #raise NotImplementedError


@then('shows the calibre-web homepage')
def calibre_web_homepage(browser):
    """shows the calibre-web homepage."""
    print("!!!!!!!")
    print(browser.title)
    print(browser.url)
    print(browser.html)
    print("!!!!!!!")
    assert browser.is_text_present('Books'), 'Book test'
 

