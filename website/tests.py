from .models import Issue, IssueScreenshot
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.test import TestCase
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from django.test.utils import override_settings
import os
import time
import sys

from django.test import LiveServerTestCase

os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = 'localhost:8082'


class MySeleniumTests(LiveServerTestCase):
    fixtures = ['initial_data.json']

    @classmethod
    def setUpClass(cls):
        print(sys.path)
        d = DesiredCapabilities.CHROME
        d["loggingPrefs"] = {"browser": "ALL"}
        option = webdriver.ChromeOptions()
        option.add_argument("window-size=1920,1080")

        # switch these
        cls.selenium = webdriver.Chrome(ChromeDriverManager(
        ).install(), desired_capabilities=d, options=option)
        super(MySeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(MySeleniumTests, cls).tearDownClass()

    @override_settings(DEBUG=True)
    def test_signup(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/signup/'))
        self.selenium.find_element("name", "username").send_keys('bugbugbug')
        self.selenium.find_element(
            "name", "email").send_keys('bugbugbug@bugbug.com')
        self.selenium.find_element(
            "name", "password1").send_keys('6:}jga,6mRKNUqMQ')
        self.selenium.find_element(
            "name", "password2").send_keys('6:}jga,6mRKNUqMQ')
        self.selenium.find_element("name", "signup_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element('tag name', 'body')
        self.assertIn('bugbugbug (0 Pts)', body.text)

    @override_settings(DEBUG=True)
    def test_login(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        self.selenium.find_element("name", "login").send_keys('bugbug')
        self.selenium.find_element("name", "password").send_keys('secret')
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element('tag name', 'body')
        self.assertIn('bugbug (0 Pts)', body.text)

    @override_settings(DEBUG=True)
    def test_post_bug(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        self.selenium.find_element("name", "login").send_keys('bugbug')
        self.selenium.find_element("name", "password").send_keys('secret')
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self.selenium.get('%s%s' % (self.live_server_url, '/report/'))
        self.selenium.find_element("name", "url").send_keys(
            'http://www.google.com/')
        self.selenium.find_element(
            "id", "description").send_keys('Description of bug')
        Imagepath = os.path.abspath(os.path.join(
            os.getcwd(), 'website/static/img/background.jpg'))
        self.selenium.find_element("name", "screenshots").send_keys(Imagepath)
        # pass captacha if in test mode
        self.selenium.find_element("name", "captcha_1").send_keys('PASSED')
        self.selenium.find_element("name", "reportbug_button").click()
        self.selenium.get('%s%s' % (self.live_server_url, '/all_activity/'))
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element('tag name', 'body')
        self.assertIn('Description of bug', body.text)


class HideImage(TestCase):
    def setUp(self):
        test_issue = Issue.objects.create(description="test", url="test.com")
        test_issue.screenshot = SimpleUploadedFile(name='test_image.jpg', content=open(
            f"website/static/images/dummy-user.png", 'rb').read(), content_type='image/png')
        test_issue.save()

    def test_on_hide(self):

        Test_Object = Issue.objects.get(url="test.com")
        issue_screenshot_list_orignal = IssueScreenshot.objects.filter(
            issue=Test_Object.id)

        Test_Object.is_hidden = True
        Test_Object.save()
        for screenshot in issue_screenshot_list_orignal:
            filename = screenshot.image.name

            try:
                if default_storage.exists(filename):
                    self.assertTrue(False, "files exist")
            except:
                pass
