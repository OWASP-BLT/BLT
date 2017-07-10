from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from django.test import LiveServerTestCase
import os
import time
os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = 'localhost:8082'

from django.test.utils import override_settings
from selenium.webdriver.firefox.webdriver import WebDriver

class MySeleniumTests(LiveServerTestCase):
    fixtures = ['initial_data.json']

    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(MySeleniumTests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(MySeleniumTests, cls).tearDownClass()


    @override_settings(DEBUG=True)
    def test_signup(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/signup/'))
        self.selenium.find_element_by_name("username").send_keys('bugbugbug')
        self.selenium.find_element_by_name("email").send_keys('bugbugbug@bugbug.com')
        self.selenium.find_element_by_name("password1").send_keys('secret123')
        self.selenium.find_element_by_name("password2").send_keys('secret123')
        self.selenium.find_element_by_name("signup_button").click()
        time.sleep(8)
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn(u'bugbugbug (0 Pts)', body.text)


    @override_settings(DEBUG=True)
    def test_login(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        self.selenium.find_element_by_name("login").send_keys('bugbug')
        self.selenium.find_element_by_name("password").send_keys('secret')
        self.selenium.find_element_by_name("login_button").click()
        time.sleep(8)
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn(u'bugbug (0 Pts)', body.text)


    @override_settings(DEBUG=True)
    def test_post_bug(self):
        self.selenium.set_page_load_timeout(70)
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        self.selenium.find_element_by_name("login").send_keys('bugbug')
        self.selenium.find_element_by_name("password").send_keys('secret')
        self.selenium.find_element_by_name("login_button").click()
        time.sleep(8)
        self.selenium.get('%s%s' % (self.live_server_url, '/report/'))
        self.selenium.find_element_by_name("url").send_keys('http://www.example.com/')
        self.selenium.find_element_by_id("description").send_keys('Description of bug')
        Imagepath=os.path.abspath(os.path.join(os.getcwd(),'website/static/img/logo.jpg'))     
        self.selenium.find_element_by_name("screenshot").send_keys(Imagepath)
        self.selenium.find_element_by_name("reportbug_button").click()
        time.sleep(3)
        self.selenium.get('%s%s' % (self.live_server_url, '/'))
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn(u'Description of bug', body.text)
    