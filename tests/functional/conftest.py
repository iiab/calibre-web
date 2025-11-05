import pytest

from urllib.parse import urljoin
from selenium import webdriver
import time


@pytest.fixture(scope="session")
def splinter_driver_kwargs(splinter_webdriver):
    """Override Chrome WebDriver options"""
    if splinter_webdriver == "chrome":
        chrome_options = webdriver.ChromeOptions()

        # List of Chromium Command Line Switches
        # https://peter.sh/experiments/chromium-command-line-switches/
        chrome_options.add_argument("--no-sandbox")

        return {"options": chrome_options}

    elif splinter_webdriver == "firefox":
        firefox_options = webdriver.FirefoxOptions()
        return {"options": firefox_options}
    else:
        raise ValueError(
            "Invalid browser passed to --splinter_Wewbdriver. Only Chrome and Firefox are allowed"
        )


@pytest.fixture
def step_context():
    """Fixture to save information to use through steps."""
    return {}


def visit_website(browser, step_context):
    step_context["ip_address"] = "localhost:8083"
    url = urljoin("".join(["http://", str(step_context["ip_address"])]), "/")
    browser.visit(url)


def login_with_username_and_password(browser, username, password):
    guest = browser.find_by_id("top_user")
    guest.click()
    browser.fill("username", username)
    browser.fill("password", password)
    button = browser.find_by_name("submit")
    button.click()


def login_if_not_logged_in(browser, username, password):
    if not browser.is_element_present_by_id("logout"):
        login_with_username_and_password(browser, username, password)


def find_video_by_title(browser, title):
    video_found = False
    count = 0

    while (not video_found) and (count <= 10):
        time.sleep(5)
        browser.reload()
        video_found = browser.is_element_present_by_xpath(f"//p[@title='{title}']", 1)
        count += 1
    return video_found
