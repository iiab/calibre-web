# Calibre-Web on IIAB

Calibre-Web is a web app that offers a clean and intuitive interface for browsing, reading, and downloading eBooks using a valid [Calibre](https://calibre-ebook.com) database.

*This software is a friendly fork of [Calibre-Web](https://github.com/janeczku/calibre-web) designed to be run inside of an Internet-in-a-Box.*

![Main screen](https://github.com/janeczku/calibre-web/wiki/images/main_screen.png)

## Features

- Mainline [Calibre-Web features](https://github.com/janeczku/calibre-web?tab=readme-ov-file#features)
- Not just books but also learning [videos, audiocasts and images](https://github.com/iiab/calibre-web/wiki#videos-and-images) most needed by your community or family
- Downloading [online media](https://github.com/iiab/calibre-web/wiki#download-online-media)

## Installation

1. If you don't have an existing IIAB, start here:

   <https://github.com/iiab/calibre-web/wiki#wrench-installation>

2. Installing on an existing Internet-in-a-Box (IIAB):

   <https://github.com/iiab/iiab/blob/master/roles/calibre-web/README.rst>

## Quick Start

0. Read the [NEW Install Instructions](#installation) above for IIAB Calibre-Web!
1. **Access Calibre-Web**: Open your browser and navigate to:

   ```
   http://localhost:8083
   ```

   or for the OPDS catalog:

   ```
   http://localhost:8083/opds
   ```

2. **Log in**: Use the default admin credentials:
   - **Username:** Admin
   - **Password:** changeme
3. **Database Setup**: If you do not have a Calibre database, download a sample from:

   ```
   https://github.com/iiab/calibre-web/raw/master/library/metadata.db
   ```

   Move it out of the Calibre-Web folder to avoid overwriting during updates.
4. **Configure Calibre Database**: In the admin interface, set the `Location of Calibre database` to the path of the folder containing your Calibre library (where `metadata.db` is located) and click "Save".
5. **Google Drive Integration**: For hosting your Calibre library on Google Drive, refer to the [Google Drive integration guide](https://github.com/iiab/calibre-web/wiki/G-Drive-Setup#using-google-drive-integration).
6. **Admin Configuration**: Configure your instance via the admin page, referring to the [Basic Configuration](https://github.com/iiab/calibre-web/wiki/Configuration#basic-configuration) and [UI Configuration](https://github.com/iiab/calibre-web/wiki/Configuration#ui-configuration) guides.

## Setup for IIAB-less Calibre-Web

Please note that this version of Calibre-Web is primarily for installation through IIAB. However, we do maintain this documentation to allow an IIAB-less setup of Calibre-Web. Currently this is done solely for our integration test workflow. This setup has been tested on openSUSE Tumbleweed.

1. Clone the repository

```bash
https://github.com/iiab/calibre-web.git
```

2. Enter the directory where you clone the repository

```bash
cd calibre-web/
```

3. Create the virtual environment and activate it

```bash
python3 -m venv venv
source /venv/bin/activate
```

4. Install all the dependencies

```bash
pip install -r requirements.txt
```

5. Download the database

```bash
wget -O app.db https://github.com/iiab/iiab/raw/refs/heads/master/roles/calibre-web/files/app.db
```

6. Create the needed library directories, and download metadata.db

```bash
sudo mkdir -p /library/calibre-web
sudo mkdir /library/downloads/
sudo wget -O /library/calibre-web/metadata.db https://github.com/iiab/iiab/raw/refs/heads/master/roles/calibre-web/files/metadata.db
sudo chown user_running_calibre-web /library/calibre-web
sudo chown user_running_calibre-web /library/calibre-web/metadata.db
sudo chown user_running_calibre-web /library/downloads/
```

Make sure to replace user_running_calibre-web with the correct username.

7. Create the log file

```bash
sudo touch /var/log/xklb.log
sudo chown user_running_calibre-web /var/log/xklb.log
```

Make sure to replace user_running_calibre-web with the correct username.

8. Copy the lb-wrapper and yt-updater scripts to /usr/local/bin

```bash
sudo cp ./scripts/lb-wrapper /usr/local/bin
sudo cp ./scripts/yt-updater /usr/local/bin
sudo chmod a+x /usr/local/bin/lb-wrapper
sudo chmod a+x /usr/local/bin/yt-updater
```

9. Finally, run calibre-web

```bash
nohup python3 cps.py &
```

10. Open your favorite browser to localhost:8083. You should see the Internet-in-a-Box branded Calibre-Web running. Login with:

- Username: admin
- Password: changeme

## Requirements

- **IIAB**: IIAB Calibre-Web is designed for running on top of an Internet-in-a-Box install
- **Python Version**: Ensure you have Python 3.7 or newer.
- **Imagemagick**: Required for cover extraction from EPUBs. Windows users may also need to install [Ghostscript](https://ghostscript.com/releases/gsdnld.html) for PDF cover extraction.
- **Optional Tools**:
  - **Calibre desktop program**: Recommended for on-the-fly conversion and metadata editing. Set the path to Calibre’s converter tool on the setup page.
  - **Kepubify tool**: Needed for Kobo device support. Download the tool and place the binary in `/opt/kepubify` on Linux or `C:\Program Files\kepubify` on Windows.

## Docker Images

[IIAB Calibre-Web](#installation) does not support Docker.

## Contributor Recognition

We would like to thank all the contributors and maintainers of Calibre-Web for their valuable input and dedication to the project. Your contributions are greatly appreciated:

- [janeczku/calibre-web](https://github.com/janeczku/calibre-web/graphs/contributors)
- [iiab/calibre-web](https://github.com/iiab/calibre-web/graphs/contributors)

## Integration tests

#### Test plans

You can find the current test plan under in the [features](features) directory. Currently, there is only one test plan, which is [basic_behavior.feature](features/basic_behavior.feature).

Here what the layout of an example test plan looks like looks like:

```
Feature: Basic behavior
    Testing basic behavior like showing home page and login

    Scenario: Home Page
        Given Calibre-Web is running
        When I go to the home page

        Then I should not see the error message
        And see homepage information
```

A scenario is a specific test. Depending on the test, some things are taken as given, when an action is performed, then a certain state is reached.

#### How the tests are implemented

The tests are implemented using pytest-splinter, pytest-bdd and Selenium. The gist of all of this is to say that these are tests using [behavior-driven development](https://en.wikipedia.org/wiki/Behavior-driven_development). Pytest-splinter is the main driver of the tests, it is what is really driving the browser through the use of Selenium.

Currently, we are limited to using Firefox and Chrome as a result of Splinter (a dependency of pytest-splinter) not supporting Chromium. If this were to change in the future though, we would probably rather use Chromium over Chrome as that is the default browser used with Raspberry Pi.

You can see tests in the [/tests/functional](tests/functional) directory. Currently there is only one test file, [test_basic_behavior.py](tests/functional/test_basic_behavior.py).

Here is an example of one test:

```
@scenario('basic_behavior.feature', 'Home Page')
def test_home_page():
    """Home Page."""


@given('Calibre-Web is running')
def _(step_context):
    """Calibre-Web is running."""
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
```

If you compare this test to the test I showed you in this test plan, then you will see that is pretty much exactly the same. Especially pay attention to the fixtures (the lines that begin with @).

#### Prerequisites

1. **Install Chrome and/or Firefox to enable Selenium testing**:

    - [Install Chrome for Ubuntu](https://linuxcapable.com/install-google-chrome-on-ubuntu-linux/) and/or

    - [Install Firefox](https://support.mozilla.org/en-US/kb/install-firefox-linux#w_install-firefox-deb-package-for-debian-based-distributions-recommended) [NB: If you are on Ubuntu Deskop you must remove the Firefox Snap with `sudo snap remove firefox`, or else the tests will fail]

2. **Enter into the directory where Calibre-Web is located**:

    ```
    cd /usr/local/calibre-web-py3
    ```

3. **Install the integration test requirements in the same virtual environment**:

   ```
   pip install -r integration-tests-requirements.txt
   ```

#### Running the tests

   If you want to watch the test run

   ```
   pytest -s --splinter-webdriver chrome
   ```

   And/or you can just run headless:

   ```
   pytest -s --splinter-webdriver chrome --splinter-headless
```

To run the tests with the Firefox browser instead, replace chrome with firefox.

## Contributing to Calibre-Web

To contribute, please check our [Contributing Guidelines](https://github.com/iiab/calibre-web/blob/master/CONTRIBUTING.md). We welcome issues, feature requests, and pull requests from the community.

### Reporting Bugs

If you encounter bugs or issues, please report them in the [issues section](https://github.com/iiab/calibre-web/issues) of the repository. Be sure to include detailed information about your setup and the problem encountered.

If your problem is generic to the [upstream janeczku/calibre-web](https://github.com/janeczku/calibre-web/issues) you may wish to report your issue there.

### Feature Requests

We welcome suggestions for new features. Please create a new issue in the repository to discuss your ideas.

## Additional Resources

- **Documentation**: Comprehensive documentation is available on the [IIAB Calibre-Web wiki](https://github.com/iiab/calibre-web/wiki) and the [upstream Calibre-Web wiki](https://github.com/janeczku/calibre-web/wiki/).
- **Community Contributions**: Explore the [community contributions](https://github.com/iiab/calibre-web/pulls) to see ongoing work and how you can get involved.

---

Thank you for using Calibre-Web! We hope you enjoy managing your eBook library with our tool.
