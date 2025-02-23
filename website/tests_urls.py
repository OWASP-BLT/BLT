# these tests seem to take too long and don't always catch everything so we're going to focus on more important tests
# import importlib
# import logging
# import os
# import shutil
# import socket
# from collections import defaultdict

# import chromedriver_autoinstaller
# from allauth.socialaccount.models import SocialApp
# from django.conf import settings
# from django.contrib.sites.models import Site
# from django.contrib.staticfiles.handlers import StaticFilesHandler
# from django.contrib.staticfiles.testing import StaticLiveServerTestCase
# from django.core.management import call_command
# from django.test.utils import override_settings
# from django.urls import reverse
# from selenium import webdriver
# from selenium.common.exceptions import TimeoutException
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait

# # Suppress Selenium logging
# logging.getLogger("selenium").setLevel(logging.WARNING)
# logging.getLogger("urllib3").setLevel(logging.WARNING)


# def find_free_port():
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.bind(("", 0))
#         s.listen(1)
#         port = s.getsockname()[1]
#         return port


# # Set a specific port for the live server
# os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = f"localhost:{find_free_port()}"


# @override_settings(
#     STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
#     DEBUG=True,
#     STATIC_URL="/static/",
#     SENTRY_DSN=None,  # Disable Sentry in tests
#     TESTING=True,
# )
# class UrlsTest(StaticLiveServerTestCase):
#     fixtures = ["initial_data.json"]
#     static_handler = StaticFilesHandler

#     @classmethod
#     def setUpClass(cls):
#         # Collect static files before running tests
#         if os.path.exists(settings.STATIC_ROOT):
#             shutil.rmtree(settings.STATIC_ROOT)
#         call_command("collectstatic", "--noinput", "--clear")

#         cls.host = "localhost"
#         cls.port = find_free_port()
#         super().setUpClass()

#         # Set up Chrome
#         chromedriver_autoinstaller.install()
#         options = webdriver.ChromeOptions()
#         options.add_argument("--headless")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--remote-debugging-port=9222")
#         options.add_argument("--window-size=1420,1080")
#         options.add_argument("--disable-extensions")
#         options.add_argument('--proxy-server="direct://"')
#         options.add_argument("--proxy-bypass-list=*")
#         options.add_argument("--start-maximized")
#         # Increase page load timeout
#         options.add_argument("--page-load-strategy=normal")

#         try:
#             cls.selenium = webdriver.Chrome(options=options)
#             # Increase timeouts for better static file loading
#             cls.selenium.set_page_load_timeout(30)
#             cls.selenium.implicitly_wait(30)
#         except Exception as e:
#             print(f"Error setting up Chrome: {e}")
#             raise

#     @classmethod
#     def tearDownClass(cls):
#         try:
#             if hasattr(cls, "selenium"):
#                 cls.selenium.quit()
#             # Don't clean up static files after tests to allow inspection
#             # if os.path.exists(settings.STATIC_ROOT):
#             #     shutil.rmtree(settings.STATIC_ROOT)
#         except Exception as e:
#             print(f"Error in teardown: {e}")
#         finally:
#             super().tearDownClass()

#     def setUp(self):
#         self.site = Site.objects.get(pk=1)
#         self.site.domain = f"{self.host}:{self.port}"
#         self.site.name = "localhost"
#         self.site.save()

#         # Delete existing SocialApp instances for the providers
#         SocialApp.objects.filter(provider__in=["github", "google", "facebook"]).delete()

#         # Create SocialApp for GitHub
#         github_app = SocialApp.objects.create(
#             provider="github",
#             name="GitHub",
#             client_id="dummy_client_id",
#             secret="dummy_secret",
#         )
#         github_app.sites.add(self.site)

#         # Create SocialApp for Google
#         google_app = SocialApp.objects.create(
#             provider="google",
#             name="Google",
#             client_id="dummy_client_id",
#             secret="dummy_secret",
#         )
#         google_app.sites.add(self.site)

#         # Create SocialApp for Facebook
#         facebook_app = SocialApp.objects.create(
#             provider="facebook",
#             name="Facebook",
#             client_id="dummy_client_id",
#             secret="dummy_secret",
#         )
#         facebook_app.sites.add(self.site)

#     def test_responses(
#         self,
#         allowed_http_codes=[200, 302, 405, 401, 404, 400],
#         credentials={},
#         default_kwargs={},
#     ):
#         module = importlib.import_module(settings.ROOT_URLCONF)
#         if credentials:
#             self.client.login(**credentials)

#         # Track errors for summary
#         errors = defaultdict(list)
#         total_urls = 0
#         successful_urls = 0

#         def check_urls(urlpatterns, prefix=""):
#             nonlocal total_urls, successful_urls

#             for pattern in urlpatterns:
#                 if hasattr(pattern, "url_patterns"):
#                     new_prefix = prefix
#                     if pattern.namespace:
#                         new_prefix = prefix + (":" if prefix else "") + pattern.namespace
#                     check_urls(pattern.url_patterns, prefix=new_prefix)
#                 params = {}
#                 skip = False

#                 regex = pattern.pattern.regex
#                 if regex.groups > 0:
#                     if regex.groups > len(list(regex.groupindex.keys())) or set(regex.groupindex.keys()) - set(
#                         default_kwargs.keys()
#                     ):
#                         skip = True
#                     else:
#                         for key in set(default_kwargs.keys()) & set(regex.groupindex.keys()):
#                             params[key] = default_kwargs[key]

#                 if hasattr(pattern, "name") and pattern.name:
#                     name = pattern.name
#                 else:
#                     skip = True
#                     name = ""
#                 fullname = (prefix + ":" + name) if prefix else name

#                 if not skip:
#                     try:
#                         url = reverse(fullname, kwargs=params)
#                         matches = [
#                             "/static/",
#                             "/socialaccounts/",
#                             "/auth/user/",
#                             "/auth/password/change/",
#                             "/auth/github/connect/",
#                             "/auth/google/connect/",
#                             "/auth/registration/",
#                             "/auth/registration/verify-email/",
#                             "/auth/registration/resend-email/",
#                             "/auth/password/reset/",
#                             "/auth/password/reset/confirm/",
#                             "/auth/login/",
#                             "/auth/logout/",
#                             "/auth/facebook/connect/",
#                             "/captcha/refresh/",
#                             "/rest-auth/user/",
#                             "/rest-auth/password/change/",
#                             "/accounts/github/login/",
#                             "/accounts/google/login/",
#                             "/accounts/facebook/login/",
#                             "/error/",
#                             "/tz_detect/set/",
#                             "/leaderboard/api/",
#                             "/api/timelogsreport/",
#                             "/oauth/slack/callback/",
#                         ]
#                         if not any(x in url for x in matches):
#                             total_urls += 1
#                             try:
#                                 print(f"\nTesting URL: {url}")  # Debug line
#                                 response = self.client.get(url, follow=True)
#                                 if response.status_code not in allowed_http_codes:
#                                     error_msg = (
#                                         f"URL {url} returned {response.status_code} "
#                                         f"(Expected: {allowed_http_codes})"
#                                     )
#                                     errors["http"].append(error_msg)
#                                     print(f"Failed with status code: {response.status_code}")  # Debug line
#                                     continue

#                                 # Only test with Selenium if the response was successful
#                                 if response.status_code in [200, 302]:
#                                     try:
#                                         test_url = f"{self.live_server_url}{url}"
#                                         print(f"Testing with Selenium: {test_url}")  # Debug line
#                                         self.selenium.get(test_url)

#                                         # Wait for page load with increased timeout
#                                         WebDriverWait(self.selenium, 30).until(
#                                             EC.presence_of_element_located((By.TAG_NAME, "body"))
#                                         )

#                                         # Wait for static resources to load
#                                         self.selenium.execute_script(
#                                             """
#                                             return new Promise((resolve) => {
#                                                 const checkReadyState = () => {
#                                                     if (document.readyState === 'complete') {
#                                                         resolve();
#                                                     } else {
#                                                         setTimeout(checkReadyState, 100);
#                                                     }
#                                                 };
#                                                 checkReadyState();
#                                             });
#                                             """
#                                         )

#                                         # Check for JavaScript errors
#                                         browser_logs = self.selenium.get_log("browser")
#                                         js_errors = []
#                                         static_404s = []
#                                         for log in browser_logs:
#                                             if log["level"] == "SEVERE":
#                                                 # Ignore Sentry errors
#                                                 if "sentry" in log["message"].lower():
#                                                     continue
#                                                 if (
#                                                     log["message"].startswith("http")
#                                                     and ("/static/" in log["message"] or "/media/" in log["message"])
#                                                     and "404" in log["message"]
#                                                 ):
#                                                     # Extract just the file path from the 404 message
#                                                     file_path = log["message"].split(" ")[0]
#                                                     static_404s.append(file_path)
#                                                 else:
#                                                     js_errors.append(log["message"])

#                                         if static_404s:
#                                             # Check if the static files exist in STATIC_ROOT
#                                             missing_files = []
#                                             for file_path in static_404s:
#                                                 relative_path = file_path.split("/static/")[-1]
#                                                 full_path = os.path.join(settings.STATIC_ROOT, relative_path)
#                                                 if not os.path.exists(full_path):
#                                                     missing_files.append(
#                                                         f"{file_path} (not found in {settings.STATIC_ROOT})"
#                                                     )
#                                                 else:
#                                                     missing_files.append(f"{file_path} (exists but not served)")

#                                             errors[url].extend(missing_files)

#                                         if js_errors:
#                                             print(f"JavaScript errors for {url}:")  # Debug line
#                                             for error in js_errors:
#                                                 print(f"  - {error}")  # Debug line
#                                             errors[url].extend(js_errors)

#                                         successful_urls += 1
#                                     except TimeoutException:
#                                         errors[url].append("Timeout waiting for page load")
#                                     except Exception as e:
#                                         errors[url].append(f"Selenium error: {str(e)}")
#                             except Exception as e:
#                                 errors[url].append(f"Request error: {str(e)}")
#                     except Exception as e:
#                         if not skip:
#                             errors[url].append(f"URL error: {str(e)}")

#         # Check all URLs
#         check_urls(module.urlpatterns)

#         # Print summary of errors
#         if errors:
#             print("\nError Summary:")
#             print("-" * 40)
#             if errors["url"]:
#                 print("\nURL Reverse Errors:")
#                 for error in errors["url"]:
#                     print(f"  - {error}")
#             if errors["http"]:
#                 print("\nHTTP Status Errors:")
#                 for error in errors["http"]:
#                     print(f"  - {error}")
#             if errors["timeout"]:
#                 print("\nTimeout Errors:")
#                 for url in errors["timeout"]:
#                     print(f"  - {url}")
#             if errors["selenium"]:
#                 print("\nSelenium Errors:")
#                 for error in errors["selenium"]:
#                     print(f"  - {error}")
#             if errors["static"]:
#                 print("\nStatic File Errors:")
#                 for error in errors["static"]:
#                     print(f"  - {error}")
#             if errors["javascript"]:
#                 print("\nJavaScript Errors:")
#                 for error in errors["javascript"]:
#                     print(f"  - {error}")
#             if errors["request"]:
#                 print("\nRequest Errors:")
#                 for error in errors["request"]:
#                     print(f"  - {error}")
#             print("\nTest Summary:")
#             print(f"Total URLs tested: {total_urls}")
#             print(f"Successful: {successful_urls}")
#             print(f"Failed: {total_urls - successful_urls}")
#             print("-" * 40)
#             self.fail("Errors found during URL testing. See above for details.")
#         else:
#             print(f"\nAll {total_urls} URLs tested successfully!")
#             print(f"Successful URLs: {successful_urls}")
