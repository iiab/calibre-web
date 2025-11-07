"""Add user feature tests."""

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

from tests.functional.conftest import login_if_not_logged_in, visit_website


@scenario("create_users.feature", "Create user 1")
def test_create_user_1():
    """Create user 1"""


@given("Calibre-Web is running and I am logged in as admin")
def _(browser, step_context):
    """Calibre-Web is running and I am logged in as admin"""
    visit_website(browser, step_context)
    login_if_not_logged_in(browser, "Admin", "changeme")


@when("I click on Admin button and create user 1")
def _(browser, step_context):
    """I click on Admin and add user 1"""
    admin_button = browser.find_by_id("top_admin")
    admin_button.click()

    add_new_user_button = browser.find_by_id("admin_new_user")
    add_new_user_button.click()

    browser.fill("name", "chloe")
    browser.fill("email", "chloe@iiab.io")
    browser.fill("password", "Chloe123!")

    save_button = browser.find_by_id("user_submit")
    save_button.click()


@then("I should see that user 1 is created")
def _(browser):
    """I should see that user 1 is created"""
    browser.is_element_present_by_id("name", 3)
    assert browser.find_by_id("name").value == "chloe", (
        "Expected to see user 1 is present"
    )


@scenario("create_users.feature", "Create user 2")
def test_create_user_2():
    """Create user 2"""


@when("I click on Admin button and create user 2")
def _(browser, step_context):
    """I click on Admin and create user 2"""
    admin_button = browser.find_by_id("top_admin")
    admin_button.click()

    add_new_user_button = browser.find_by_id("admin_new_user")
    add_new_user_button.click()

    browser.fill("name", "ella")
    browser.fill("email", "ella@iiab.io")
    browser.fill("password", "Ella123!")

    save_button = browser.find_by_id("user_submit")
    save_button.click()


@then("I should see that user 2 is created")
def _(browser):
    """I should see that user 2 is created"""
    browser.is_element_present_by_id("name", 3)
    assert browser.find_by_id("name").value == "ella", (
        "Expected to see user 2 is present"
    )
