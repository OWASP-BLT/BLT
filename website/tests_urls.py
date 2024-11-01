import importlib
import os

import chromedriver_autoinstaller
from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db import transaction
from django.urls import reverse
from selenium.webdriver.chrome.service import Service

os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = "localhost:8082"

from selenium import webdriver

service = Service(chromedriver_autoinstaller.install())

options = webdriver.ChromeOptions()
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
driver = webdriver.Chrome(service=service, options=options)


class UrlsTest(StaticLiveServerTestCase):
    fixtures = ["initial_data.json"]

    @classmethod
    def setUpClass(cls):
        cls.selenium = driver
        super(UrlsTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(UrlsTest, cls).tearDownClass()

    def setUp(self):
        site = Site.objects.get(pk=1)
        site.domain = "localhost:8082"
        site.name = "localhost"
        site.save()

        # Delete existing SocialApp instances for the providers
        SocialApp.objects.filter(provider__in=["github", "google", "facebook"]).delete()

        # Create SocialApp for GitHub
        github_app = SocialApp.objects.create(
            provider="github",
            name="GitHub",
            client_id="dummy_client_id",
            secret="dummy_secret",
        )
        github_app.sites.add(site)

        # Create SocialApp for Google
        google_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="dummy_client_id",
            secret="dummy_secret",
        )
        google_app.sites.add(site)

        # Create SocialApp for Facebook
        facebook_app = SocialApp.objects.create(
            provider="facebook",
            name="Facebook",
            client_id="dummy_client_id",
            secret="dummy_secret",
        )
        facebook_app.sites.add(site)

    def test_responses(
        self,
        allowed_http_codes=[200, 302, 405, 401, 404],
        credentials={},
        default_kwargs={},
    ):
        module = importlib.import_module(settings.ROOT_URLCONF)
        if credentials:
            self.client.login(**credentials)

        def check_urls(urlpatterns, prefix=""):
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
                    if regex.groups > len(list(regex.groupindex.keys())) or set(
                        regex.groupindex.keys()
                    ) - set(default_kwargs.keys()):
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
                    url = reverse(fullname, kwargs=params)
                    matches = [
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
                    ]
                    if not any(x in url for x in matches):
                        with transaction.atomic():
                            response = self.client.get(url)
                            self.assertIn(response.status_code, allowed_http_codes, msg=url)
                            self.selenium.get("%s%s" % (self.live_server_url, url))

                            for entry in self.selenium.get_log("browser"):
                                self.assertNotIn("SyntaxError", str(entry), msg=url)

        check_urls(module.urlpatterns)

    def test_github_login(self):
        url = reverse("github_login")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_google_login(self):
        url = reverse("google_login")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_facebook_login(self):
        url = reverse("facebook_login")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_github_callback(self):
        url = reverse("github_callback")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_google_callback(self):
        url = reverse("google_callback")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_facebook_callback(self):
        url = reverse("facebook_callback")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_github_connect(self):
        url = reverse("github_connect")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_google_connect(self):
        url = reverse("google_connect")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)

    def test_facebook_connect(self):
        url = reverse("facebook_connect")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302, 405, 401, 404], msg=url)
