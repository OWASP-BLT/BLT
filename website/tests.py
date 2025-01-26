import os

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

from .models import Activity, ContentType, Issue, IssueScreenshot, User

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
        self.selenium.find_element("name", "captcha_1").send_keys("PASSED")
        self.selenium.find_element("name", "signup_button").click()
        WebDriverWait(self.selenium, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("bugbugbug (0 Pts)", body.text)

    @override_settings(DEBUG=True)
    def test_login(self):
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("bugbug (0 Pts)", body.text)

    @override_settings(DEBUG=True)
    def test_post_bug_full_url(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.selenium.get("%s%s" % (self.live_server_url, "/report/"))
        self.selenium.find_element("name", "url").send_keys("https://blt.owasp.org/report/")
        self.selenium.find_element("id", "description").send_keys("XSS Attack on Google")  # title of bug
        self.selenium.find_element("id", "markdownInput").send_keys("Description of bug")
        Imagepath = os.path.abspath(os.path.join(os.getcwd(), "website/static/img/background.jpg"))
        self.selenium.find_element("name", "screenshots").send_keys(Imagepath)
        # pass captacha if in test mode
        self.selenium.find_element("name", "captcha_1").send_keys("PASSED")
        self.selenium.find_element("name", "reportbug_button").click()
        self.selenium.get("%s%s" % (self.live_server_url, "/all_activity/"))
        WebDriverWait(self.selenium, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("XSS Attack on Google", body.text)

    @override_settings(DEBUG=True)
    def test_post_bug_domain_url(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.selenium.get("%s%s" % (self.live_server_url, "/report/"))
        self.selenium.find_element("name", "url").send_keys("https://google.com")
        self.selenium.find_element("id", "description").send_keys("XSS Attack on Google")  # title of bug
        self.selenium.find_element("id", "markdownInput").send_keys("Description of bug")
        Imagepath = os.path.abspath(os.path.join(os.getcwd(), "website/static/img/background.jpg"))
        self.selenium.find_element("name", "screenshots").send_keys(Imagepath)
        # pass captacha if in test mode
        self.selenium.find_element("name", "captcha_1").send_keys("PASSED")
        self.selenium.find_element("name", "reportbug_button").click()
        self.selenium.get("%s%s" % (self.live_server_url, "/all_activity/"))
        WebDriverWait(self.selenium, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
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


# from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

# from .models import Project


# class ProjectListViewTests(TestCase):
#     def test_add_project_with_branch_url(self):
#         url = reverse("project_list")
#         github_url = (
#             "https://github.com/OWASP/www-project-top-10-infrastructure-security-risks/tree/main"
#         )
#         response = self.client.post(url, {"github_url": github_url})

#         # Check if the response is a redirect to the project list
#         self.assertRedirects(response, url)

#         # Check if the appropriate success message is displayed
#         messages = list(get_messages(response.wsgi_request))
#         self.assertTrue(any("Project added successfully." in str(message) for message in messages))

#         # Ensure the project was created
#         self.assertTrue(Project.objects.filter(github_url=github_url).exists())


class RemoveUserFromIssueTest(TestCase):
    def setUp(self):
        # Create a user, an anonymous user, and an issue
        self.user = User.objects.create_user(username="testuser", password="password")
        self.anonymous_user = User.objects.create_user(username="anonymous", password="password")

        self.issue = Issue.objects.create(user=self.user, description="Test Issue")

        # Create corresponding activity
        self.activity = Activity.objects.create(
            user=self.user,
            content_type=ContentType.objects.get_for_model(Issue),
            object_id=self.issue.id,
        )

    def test_remove_user_from_issue(self):
        # Only the issue poster can delete own issue
        self.client.login(username="testuser", password="password")

        url = reverse("remove_user_from_issue", args=[self.issue.id])
        response = self.client.post(url, follow=True)

        self.issue.refresh_from_db()
        self.activity.refresh_from_db()

        # Activity user should be set to anonymous and issue user to None
        self.assertEqual(self.activity.user.username, "anonymous")
        self.assertIsNone(self.issue.user)
