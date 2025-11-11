"""Add user feature tests."""

import pytest
from pytest_bdd import given, scenario, then, when, parsers

from urllib.parse import urljoin
from selenium import webdriver
import os
import time

from tests.functional.conftest import login_if_not_logged_in, visit_website


@scenario("create_users.feature", "Create users")
def test_create_user_1():
    """Create users"""


@given("Calibre-Web is running and I am logged in as admin")
def _(browser, step_context):
    """Calibre-Web is running and I am logged in as admin"""
    visit_website(browser, step_context)
    login_if_not_logged_in(browser, "Admin", "changeme")


@when(
    parsers.parse(
        "I click on Admin button and create user with {username}, {password}, and {email}"
    )
)
def _(browser, username, password, email):
    admin_button = browser.find_by_id("top_admin")
    admin_button.click()

    add_new_user_button = browser.find_by_id("admin_new_user")
    add_new_user_button.click()

    browser.fill("name", username)
    browser.fill("email", email)
    browser.fill("password", password)

    save_button = browser.find_by_id("user_submit")
    save_button.click()


@then(parsers.parse("I should see that {username} is created"))
def _(browser, username):
    time.sleep(0.5)
    assert browser.find_by_id("name").value == username, (
        f"Expected to see user {username} is present"
    )
