import os

import chromedriver_autoinstaller
from django.test import LiveServerTestCase
from django.test.utils import override_settings
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
    def test_company_trademark(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get("%s%s" % (self.live_server_url, "/accounts/login/"))
        self.selenium.find_element("name", "login").send_keys("bugbug")
        self.selenium.find_element("name", "password").send_keys("secret")
        self.selenium.find_element("name", "login_button").click()
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        self.selenium.get("%s%s" % (self.live_server_url, "/company/58/dashboard/edit_domain/99/"))
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.NAME, "trademarkInput"))
        )
        self.selenium.find_element("name", "trademarkInput").send_keys("bugbug.com")
        self.selenium.find_element("name", "addtrademark_button").click()
        self.selenium.get("%s%s" % (self.live_server_url, "/company/domain/99/"))
        WebDriverWait(self.selenium, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        body = self.selenium.find_element("tag name", "body")
        self.assertIn("bugbug.com", body.text)
