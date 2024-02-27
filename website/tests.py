import os
import unittest
import chromedriver_autoinstaller
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import LiveServerTestCase, TestCase
from django.test.utils import override_settings
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import Issue, IssueScreenshot

from unittest.mock import patch
from django.urls import reverse
from django.test import RequestFactory, TestCase
from .views import GoogleLogin, GithubLogin

os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = "localhost:8082"


class MySeleniumTests(LiveServerTestCase):
    fixtures = ["initial_data.json"]

    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("window-size=1920,1080")
        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        service = Service(chromedriver_autoinstaller.install())
        cls.selenium = webdriver.Chrome(service=service, options=options)

        super(MySeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(MySeleniumTests, cls).tearDownClass()

    @override_settings(DEBUG=True)
    def test_signup(self):
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/signup/"))
        self.selenium.find_element("name", "username").send_keys("bugbugbug")
        self.selenium.find_element("name", "email").send_keys("bugbugbug@bugbug.com")
        self.selenium.find_element("name", "password1").send_keys("6:}jga,6mRKNUqMQ")
        self.selenium.find_element("name", "password2").send_keys("6:}jga,6mRKNUqMQ")
        self.selenium.find_element("name", "signup_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("bugbugbug (0 Pts)", body.text)

    @override_settings(DEBUG=True)
    def test_login(self):
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("bugbug (0 Pts)", body.text)

    @override_settings(DEBUG=True)
    def test_post_bug_full_url(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self.selenium.get("%s%s" % (self.live_server_url, "/report/"))
        self.selenium.find_element("name", "url").send_keys("https://blt.owasp.org/report/")
        self.selenium.find_element("id", "description").send_keys(
            "XSS Attack on Google"
        )  # title of bug
        self.selenium.find_element("id", "markdownInput").send_keys("Description of bug")
        Imagepath = os.path.abspath(os.path.join(os.getcwd(), "website/static/img/background.jpg"))
        self.selenium.find_element("name", "screenshots").send_keys(Imagepath)
        # pass captacha if in test mode
        self.selenium.find_element("name", "captcha_1").send_keys("PASSED")
        self.selenium.find_element("name", "reportbug_button").click()
        self.selenium.get("%s%s" % (self.live_server_url, "/all_activity/"))
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("XSS Attack on Google", body.text)

    @override_settings(DEBUG=True)
    def test_post_bug_domain_url(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self.selenium.get("%s%s" % (self.live_server_url, "/report/"))
        self.selenium.find_element("name", "url").send_keys("https://google.com")
        self.selenium.find_element("id", "description").send_keys(
            "XSS Attack on Google"
        )  # title of bug
        self.selenium.find_element("id", "markdownInput").send_keys("Description of bug")
        Imagepath = os.path.abspath(os.path.join(os.getcwd(), "website/static/img/background.jpg"))
        self.selenium.find_element("name", "screenshots").send_keys(Imagepath)
        # pass captacha if in test mode
        self.selenium.find_element("name", "captcha_1").send_keys("PASSED")
        self.selenium.find_element("name", "reportbug_button").click()
        self.selenium.get("%s%s" % (self.live_server_url, "/all_activity/"))
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("XSS Attack on Google", body.text)


class HideImage(TestCase):
    def setUp(self):
        test_issue = Issue.objects.create(description="test", url="test.com")
        test_issue.screenshot = SimpleUploadedFile(
            name="test_image.jpg",
            content=open("website/static/images/dummy-user.png", "rb").read(),
            content_type="image/png",
        )
        test_issue.save()

    def test_on_hide(self):
        Test_Object = Issue.objects.get(url="test.com")
        issue_screenshot_list_orignal = IssueScreenshot.objects.filter(issue=Test_Object.id)

        Test_Object.is_hidden = True
        Test_Object.save()
        issue_screenshot_list_new = IssueScreenshot.objects.filter(issue=Test_Object.id)

        for screenshot in issue_screenshot_list_orignal:
            filename = screenshot.image.name

            if default_storage.exists(filename):
                self.assertTrue(False, "files exist")
        for screenshot in issue_screenshot_list_new:
            filename = screenshot.image.name

            if "hidden" not in filename:
                self.assertFalse(True, "files rename failed")

class TestGoogleLogin(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_callback_url(self):
        view = GoogleLogin()
        request = self.factory.get("/auth/google/")
        request.session = {}
        view.request = request

        def mock_reverse(url_name):
            if url_name == "google_callback":
                return "http://example.com/accounts/google/login/callback/"
            else:
                raise ValueError("Unexpected URL name")

        def mock_build_absolute_uri(uri):
            return "http://example.com" + uri

        with patch("django.urls.reverse", side_effect=mock_reverse):
            with patch("django.http.HttpRequest.build_absolute_uri", side_effect=mock_build_absolute_uri):
                callback_url = view.callback_url

        self.assertEqual(callback_url, "http://example.com/accounts/google/login/callback/")

class TestGithubLogin(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_callback_url(self):
        view = GithubLogin()
        request = self.factory.get("auth/github/")
        request.session = {}
        view.request = request

        def mock_reverse(url_name):
            if url_name == "github_callback":
                return "http://example.com/accounts/github/login/callback/"
            else:
                raise ValueError("Unexpected URL name")

        def mock_build_absolute_uri(uri):
            return "http://example.com" + uri

        with patch("django.urls.reverse", side_effect=mock_reverse):
            with patch("django.http.HttpRequest.build_absolute_uri", side_effect=mock_build_absolute_uri):
                callback_url = view.callback_url

        self.assertEqual(callback_url, "http://example.com/accounts/github/login/callback/")