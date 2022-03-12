from django import test
from django.urls import reverse
from django.conf import settings
import importlib


class UrlsTest(test.TestCase):
    fixtures = ["initial_data.json"]

    def test_responses(
        self,
        allowed_http_codes=[200, 302, 405],
        credentials={},
        logout_url="",
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
                        new_prefix = (
                            prefix + (":" if prefix else "") + pattern.namespace
                        )
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
                        for key in set(default_kwargs.keys()) & set(
                            regex.groupindex.keys()
                        ):
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
                        "/captcha/refresh/",
                        "/rest-auth/user/",
                        "/rest-auth/password/change/",
                        "/accounts/github/login/",
                        "/accounts/google/login/",
                        "/accounts/facebook/login/",
                        "/error/",
                        "/tellme/post_feedback/",
                    ]
                    if not any(x in url for x in matches):
                        response = self.client.get(url)
                        self.assertIn(response.status_code, allowed_http_codes, msg=url)

                        status = (
                            ""
                            if response.status_code == 200
                            else str(response.status_code) + " "
                        )
                        if url == logout_url and credentials:
                            self.client.login(**credentials)


        check_urls(module.urlpatterns)
