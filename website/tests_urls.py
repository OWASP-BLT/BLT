import importlib
import logging
import os
import shutil
import socket
from collections import defaultdict

import chromedriver_autoinstaller
from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.urls import reverse
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Suppress Selenium logging
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        return port


# Set a specific port for the live server
os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = f"localhost:{find_free_port()}"


class UrlsTest(StaticLiveServerTestCase):
    fixtures = ["initial_data.json"]

    @classmethod
    def setUpClass(cls):
        # Collect static files before running tests
        if os.path.exists(settings.STATIC_ROOT):
            shutil.rmtree(settings.STATIC_ROOT)
        call_command("collectstatic", "--noinput", "--clear")

        cls.host = "localhost"
        cls.port = find_free_port()
        super().setUpClass()

        # Set up Chrome
        chromedriver_autoinstaller.install()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--window-size=1420,1080")
        options.add_argument("--disable-extensions")
        options.add_argument('--proxy-server="direct://"')
        options.add_argument("--proxy-bypass-list=*")
        options.add_argument("--start-maximized")

        try:
            cls.selenium = webdriver.Chrome(options=options)
            cls.selenium.set_page_load_timeout(10)
            cls.selenium.implicitly_wait(10)
        except Exception as e:
            print(f"Error setting up Chrome: {e}")
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            if hasattr(cls, "selenium"):
                cls.selenium.quit()
            # Clean up collected static files
            if os.path.exists(settings.STATIC_ROOT):
                shutil.rmtree(settings.STATIC_ROOT)
        except Exception as e:
            print(f"Error in teardown: {e}")
        finally:
            super().tearDownClass()

    def setUp(self):
        self.site = Site.objects.get(pk=1)
        self.site.domain = f"{self.host}:{self.port}"
        self.site.name = "localhost"
        self.site.save()

        # Delete existing SocialApp instances for the providers
        SocialApp.objects.filter(provider__in=["github", "google", "facebook"]).delete()

        # Create SocialApp for GitHub
        github_app = SocialApp.objects.create(
            provider="github",
            name="GitHub",
            client_id="dummy_client_id",
            secret="dummy_secret",
        )
        github_app.sites.add(self.site)

        # Create SocialApp for Google
        google_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="dummy_client_id",
            secret="dummy_secret",
        )
        google_app.sites.add(self.site)

        # Create SocialApp for Facebook
        facebook_app = SocialApp.objects.create(
            provider="facebook",
            name="Facebook",
            client_id="dummy_client_id",
            secret="dummy_secret",
        )
        facebook_app.sites.add(self.site)

    def test_responses(
        self,
        allowed_http_codes=[200, 302, 405, 401, 404, 400],
        credentials={},
        default_kwargs={},
    ):
        module = importlib.import_module(settings.ROOT_URLCONF)
        if credentials:
            self.client.login(**credentials)

        # Track errors for summary
        errors = defaultdict(list)
        total_urls = 0
        successful_urls = 0

        def check_urls(urlpatterns, prefix=""):
            nonlocal total_urls, successful_urls

            for pattern in urlpatterns:
                if hasattr(pattern, "url_patterns"):
                    new_prefix = prefix
                    if pattern.namespace:
                        new_prefix = prefix + (":" if prefix else "") + pattern.namespace
                    check_urls(pattern.url_patterns, prefix=new_prefix)
                params = {}
                skip = False

                regex = pattern.pattern.regex
                if regex.groups > 0:
                    if regex.groups > len(list(regex.groupindex.keys())) or set(regex.groupindex.keys()) - set(
                        default_kwargs.keys()
                    ):
                        skip = True
                    else:
                        for key in set(default_kwargs.keys()) & set(regex.groupindex.keys()):
                            params[key] = default_kwargs[key]

                if hasattr(pattern, "name") and pattern.name:
                    name = pattern.name
                else:
                    skip = True
                    name = ""
                fullname = (prefix + ":" + name) if prefix else name

                if not skip:
                    try:
                        url = reverse(fullname, kwargs=params)
                        matches = [
                            "/static/",
                            "/socialaccounts/",
                            "/auth/user/",
                            "/auth/password/change/",
                            "/auth/github/connect/",
                            "/auth/google/connect/",
                            "/auth/registration/",
                            "/auth/registration/verify-email/",
                            "/auth/registration/resend-email/",
                            "/auth/password/reset/",
                            "/auth/password/reset/confirm/",
                            "/auth/login/",
                            "/auth/logout/",
                            "/auth/facebook/connect/",
                            "/captcha/refresh/",
                            "/rest-auth/user/",
                            "/rest-auth/password/change/",
                            "/accounts/github/login/",
                            "/accounts/google/login/",
                            "/accounts/facebook/login/",
                            "/error/",
                            "/tz_detect/set/",
                            "/leaderboard/api/",
                            "/api/timelogsreport/",
                            "/oauth/slack/callback/",
                        ]
                        if not any(x in url for x in matches):
                            total_urls += 1
                            try:
                                response = self.client.get(url, follow=True)
                                if response.status_code not in allowed_http_codes:
                                    errors["http"].append(f"URL {url} returned {response.status_code}")
                                    continue

                                # Only test with Selenium if the response was successful
                                if response.status_code in [200, 302]:
                                    try:
                                        test_url = f"{self.live_server_url}{url}"
                                        self.selenium.get(test_url)

                                        # Wait for page load with reduced timeout
                                        WebDriverWait(self.selenium, 5).until(
                                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                                        )

                                        # Check for JavaScript errors
                                        browser_logs = self.selenium.get_log("browser")
                                        js_errors = []
                                        static_404s = []
                                        for log in browser_logs:
                                            if log["level"] == "SEVERE":
                                                if (
                                                    log["message"].startswith("http")
                                                    and ("/static/" in log["message"] or "/media/" in log["message"])
                                                    and "404" in log["message"]
                                                ):
                                                    static_404s.append(log["message"])
                                                else:
                                                    js_errors.append(log["message"])

                                        if static_404s:
                                            errors["static"].append(
                                                f"{url}: Missing static files:\n    " + "\n    ".join(static_404s)
                                            )

                                        if js_errors:
                                            errors["javascript"].append(f"{url}: {'; '.join(js_errors)}")

                                        if not (static_404s or js_errors):
                                            successful_urls += 1

                                    except TimeoutException:
                                        errors["timeout"].append(url)
                                    except Exception as e:
                                        errors["selenium"].append(f"{url}: {str(e)}")
                            except Exception as e:
                                errors["request"].append(f"{url}: {str(e)}")
                    except Exception as e:
                        errors["url"].append(f"{fullname}: {str(e)}")

        check_urls(module.urlpatterns)

        # Print error summary if there were any errors
        if errors:
            print("\nError Summary:")
            print("-" * 40)
            if errors["url"]:
                print("\nURL Reverse Errors:")
                for error in errors["url"]:
                    print(f"  - {error}")
            if errors["http"]:
                print("\nHTTP Status Errors:")
                for error in errors["http"]:
                    print(f"  - {error}")
            if errors["timeout"]:
                print("\nTimeout Errors:")
                for url in errors["timeout"]:
                    print(f"  - {url}")
            if errors["selenium"]:
                print("\nSelenium Errors:")
                for error in errors["selenium"]:
                    print(f"  - {error}")
            if errors["static"]:
                print("\nStatic File Errors:")
                for error in errors["static"]:
                    print(f"  - {error}")
            if errors["javascript"]:
                print("\nJavaScript Errors:")
                for error in errors["javascript"]:
                    print(f"  - {error}")
            if errors["request"]:
                print("\nRequest Errors:")
                for error in errors["request"]:
                    print(f"  - {error}")
            print("\nTest Summary:")
            print(f"Total URLs tested: {total_urls}")
            print(f"Successful: {successful_urls}")
            print(f"Failed: {total_urls - successful_urls}")
            print("-" * 40)

            # Fail the test if there were errors
            self.fail("URL testing failed. See error summary above.")
