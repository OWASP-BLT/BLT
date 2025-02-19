import os
import time

import chromedriver_autoinstaller
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, LiveServerTestCase, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import (
    Activity,
    ContentType,
    Domain,
    GitHubIssue,
    GitHubReview,
    Issue,
    IssueScreenshot,
    Organization,
    Points,
    Project,
    User,
    UserProfile,
)

os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = "localhost:8082"


class MySeleniumTests(LiveServerTestCase):
    fixtures = ["initial_data.json"]

    @classmethod
    def setUpClass(cls):
        super(MySeleniumTests, cls).setUpClass()

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--remote-debugging-pipe")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        try:
            service = Service(chromedriver_autoinstaller.install())
            cls.selenium = webdriver.Chrome(service=service, options=options)
            cls.selenium.set_page_load_timeout(30)
            cls.selenium.implicitly_wait(30)
        except Exception as e:
            print(f"Error setting up Chrome: {e}")
            raise

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(MySeleniumTests, cls).tearDownClass()

    @override_settings(DEBUG=True)
    def test_signup(self):
        base_url = "%s%s" % (self.live_server_url, "/accounts/signup/")
        self.selenium.get(base_url)

        # Fill in the form fields
        username = self.selenium.find_element("name", "username")
        email = self.selenium.find_element("name", "email")
        password1 = self.selenium.find_element("name", "password1")
        password2 = self.selenium.find_element("name", "password2")
        captcha = self.selenium.find_element("name", "captcha_1")

        username.send_keys("bugbugbug")
        email.send_keys("bugbugbug@bugbug.com")
        password1.send_keys("6:}jga,6mRKNUqMQ")
        password2.send_keys("6:}jga,6mRKNUqMQ")
        captcha.send_keys("PASSED")

        # Find and scroll to the signup button
        signup_button = self.selenium.find_element("name", "signup_button")
        scroll_script = "arguments[0].scrollIntoView(true);"
        self.selenium.execute_script(scroll_script, signup_button)

        # Wait for any animations to complete
        time.sleep(1)

        # Try clicking with JavaScript if regular click fails
        try:
            signup_button.click()
        except ElementClickInterceptedException:
            click_script = "arguments[0].click();"
            self.selenium.execute_script(click_script, signup_button)

        # Wait for and verify the result
        body_locator = (By.TAG_NAME, "body")
        wait = WebDriverWait(self.selenium, 30)
        wait.until(EC.presence_of_element_located(body_locator))

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
        self.client.post(url, follow=True)  # Remove unused response variable

        self.issue.refresh_from_db()
        self.activity.refresh_from_db()

        # Activity user should be set to anonymous and issue user to None
        self.assertEqual(self.activity.user.username, "anonymous")
        self.assertIsNone(self.issue.user)


class LeaderboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")

        # Create user profiles
        self.profile1, _ = UserProfile.objects.get_or_create(user=self.user1)
        self.profile2, _ = UserProfile.objects.get_or_create(user=self.user2)

        # Set GitHub URLs
        self.profile1.github_url = "https://github.com/user1"
        self.profile1.save()
        self.profile2.github_url = "https://github.com/user2"
        self.profile2.save()

        # Create test domain and issues
        self.domain = Domain.objects.create(name="example.com", url="http://example.com")
        self.issue1 = Issue.objects.create(user=self.user1, domain=self.domain)
        self.issue2 = Issue.objects.create(user=self.user2, domain=self.domain)

        # Create points for users
        Points.objects.create(user=self.user1, score=50)
        Points.objects.create(user=self.user1, score=30)
        Points.objects.create(user=self.user2, score=40)

        # Create GitHub PRs
        self.pr1 = GitHubIssue.objects.create(
            user_profile=self.profile1,
            type="pull_request",
            is_merged=True,
            title="Test PR 1",
            state="closed",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/test/test/pull/1",
            issue_id=1,
        )
        self.pr2 = GitHubIssue.objects.create(
            user_profile=self.profile2,
            type="pull_request",
            is_merged=True,
            title="Test PR 2",
            state="closed",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/test/test/pull/2",
            issue_id=2,
        )

        # Create GitHub Reviews
        self.review1 = GitHubReview.objects.create(
            reviewer=self.profile1,
            state="APPROVED",
            submitted_at=timezone.now(),
            pull_request=self.pr1,
            review_id=1,
            url="https://github.com/test/test/pull/1/reviews/1",
        )
        self.review2 = GitHubReview.objects.create(
            reviewer=self.profile2,
            state="CHANGES_REQUESTED",
            submitted_at=timezone.now(),
            pull_request=self.pr2,
            review_id=2,
            url="https://github.com/test/test/pull/2/reviews/2",
        )

    def test_global_leaderboard(self):
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leaderboard_global.html")

        # Check if all three leaderboard sections are present
        self.assertContains(response, "Global Leaderboard")
        self.assertContains(response, "Pull Request Leaderboard")
        self.assertContains(response, "Code Review Leaderboard")

        # Check points leaderboard
        self.assertContains(response, "user1")  # user1 has 80 points total
        self.assertContains(response, "user2")  # user2 has 40 points total
        self.assertContains(response, "80")
        self.assertContains(response, "40")

        # Check PR leaderboard
        self.assertContains(response, "https://github.com/user1")
        self.assertContains(response, "https://github.com/user2")

        # Check code review leaderboard
        self.assertContains(response, "Reviews: 1")  # Each user has 1 review


class ProjectPageTest(TestCase):
    """Test cases for project page functionality"""

    def setUp(self):
        """Set up test data"""
        self.project = Project.objects.create(
            name="Test Project", slug="test-project", description="A test project description"
        )

    def test_project_page_content(self):
        """Test that project page loads and displays content correctly"""
        url = reverse("project_detail", kwargs={"slug": self.project.slug})
        response = self.client.get(url)

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.name)
        self.assertContains(response, self.project.description)


class OrganizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")
        self.client.login(username="testuser", password="testpass123")

    def test_create_and_list_organization(self):
        # Test organization creation
        org_name = "Test Organization"
        org_url = "https://test-org.com"
        org_data = {
            "organization_name": org_name,
            "organization_url": org_url,
            "support_email": "support@test-org.com",
            "twitter_url": "https://twitter.com/testorg",
            "facebook_url": "https://facebook.com/testorg",
            "email": "manager@test-org.com",
        }

        response = self.client.post(reverse("register_organization"), org_data)
        # Should redirect after success
        self.assertEqual(response.status_code, 302)

        # Verify organization was created
        org = Organization.objects.filter(name=org_name).first()
        self.assertIsNotNone(org)
        self.assertEqual(org.url, org_url)
        self.assertEqual(org.email, "support@test-org.com")
        self.assertEqual(org.twitter, "https://twitter.com/testorg")
        self.assertEqual(org.facebook, "https://facebook.com/testorg")
        self.assertEqual(org.admin, self.user)
        self.assertTrue(org.is_active)

        # Test organizations list page
        response = self.client.get(reverse("organizations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, org_name)
        self.assertContains(response, org_url)
