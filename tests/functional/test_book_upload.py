"""Book upload feature tests."""

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


@scenario("book_upload.feature", "Upload book 1")
def test_upload_book_1():
    """Upload book 1"""


@given("Calibre-Web is running and I am logged in as admin")
def _(browser, step_context):
    """Calibre-Web is running and I am logged in as admin"""
    step_context["ip_address"] = "localhost:8083"
    visit_website(browser, step_context)
    login_if_not_logged_in(browser, "Admin", "changeme")


@when("I click on upload and upload the first book")
def _(browser, step_context):
    """I click on upload and upload the first book"""
    filename = "tests/functional/files/The_King_In_Yellow.epub"
    file = os.path.join(os.getcwd(), filename)
    browser.fill("btn-upload", file)


@then("I should see book 1")
def _(browser):
    """I should see book 1"""
    assert browser.find_by_id("title").value == "The King in Yellow", (
        "Expected to see first book title present"
    )

    assert browser.find_by_id("authors").value == "Robert W. Chambers", (
        "Expected to see first book author present"
    )


@scenario("book_upload.feature", "Upload book 2")
def test_upload_book_2():
    """Upload book 2"""


@when("I click on upload and upload the second book")
def _(browser, step_context):
    """I click on upload and upload the second book"""
    filename = "tests/functional/files/The_Black_Tulip.epub"
    file = os.path.join(os.getcwd(), filename)
    browser.fill("btn-upload", file)


@then("I should see book 2")
def _(browser):
    """I should see book 2."""
    assert browser.find_by_id("title").value == "The black tulip", (
        "Expected to see second book title present"
    )

    assert browser.find_by_id("authors").value == "Alexandre Dumas & Auguste Maquet", (
        "Expected to see second book authors present"
    )
