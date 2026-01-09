from datetime import datetime

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from pytz.tzinfo import BaseTzInfo

from tz_detect.templatetags.tz_detect import tz_detect
from tz_detect.utils import convert_header_name, offset_to_timezone
from tz_detect.views import SetOffsetView


class ViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def add_session(self, request):
        get_response = lambda x: HttpResponse("")
        SessionMiddleware(get_response).process_request(request)

    def test_xhr_valid(self):
        request = self.factory.post("/abc", {"offset": "-60"})
        self.add_session(request)

        response = SetOffsetView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("detected_tz", request.session)
        self.assertIsInstance(request.session["detected_tz"], int)

    def test_xhr_bad_method(self):
        request = self.factory.get("/abc")
        self.add_session(request)

        response = SetOffsetView.as_view()(request)
        self.assertEqual(response.status_code, 405)

    def test_xhr_no_offset(self):
        request = self.factory.post("/abc")
        self.add_session(request)

        response = SetOffsetView.as_view()(request)
        self.assertEqual(response.status_code, 400)

    def test_xhr_bad_offset(self):
        request = self.factory.post("/abc", {"offset": "12foo34"})
        self.add_session(request)

        response = SetOffsetView.as_view()(request)
        self.assertEqual(response.status_code, 400)


class OffsetToTimezoneTestCase(TestCase):

    # Examples offsets (in hours), and the expected timezones for the beginning and middle of the year.
    example_offsets_timezones = [
        # Note: These hours are in JavaScript's Date.getTimezoneOffset() convention,
        # so the sign is reversed compared to conventional UTC offset notation.
        (12, ("Pacific/Midway", "Pacific/Midway")),
        (11, ("Pacific/Midway", "Pacific/Midway")),
        # USA:
        (10, ("America/Adak", "Pacific/Honolulu")),  # HST, HST
        (9, ("America/Anchorage", "America/Adak")),  # AKST, HDT
        (8, ("America/Los_Angeles", "America/Anchorage")),  # PST, AKDT
        (7, ("America/Denver", "America/Phoenix")),  # MST, PDT
        (6, ("America/Chicago", "America/Denver")),  # CST, MDT
        (5, ("America/New_York", "America/Chicago")),  # EST, CDT
        (4, ("America/Porto_Velho", "America/New_York")),  # AMT, EDT
        (3, ("America/Belem", "America/Belem")),
        (2, ("America/Noronha", "America/Noronha")),
        (1, ("America/Scoresbysund", "Atlantic/Cape_Verde")),
        # Central Europe:
        (0, ("Europe/London", "Africa/Abidjan")),  # GMT, GMT
        (-1, ("Europe/Berlin", "Europe/London")),  # CET, BST
        (-2, ("Europe/Kaliningrad", "Europe/Kaliningrad")),
        (-3, ("Europe/Moscow", "Europe/Moscow")),
        (-4, ("Europe/Astrakhan", "Europe/Astrakhan")),
        (-5, ("Asia/Yekaterinburg", "Asia/Yekaterinburg")),
        (-6, ("Asia/Urumqi", "Asia/Urumqi")),
        (-7, ("Asia/Novosibirsk", "Asia/Novosibirsk")),
        (-8, ("Asia/Shanghai", "Asia/Shanghai")),
        (-9, ("Asia/Tokyo", "Asia/Tokyo")),
        (-10, ("Asia/Vladivostok", "Asia/Vladivostok")),
        (-11, ("Asia/Magadan", "Asia/Magadan")),
        (-12, ("Asia/Kamchatka", "Asia/Kamchatka")),
        (-13, ("Antarctica/McMurdo", "Pacific/Apia")),
        (-14, ("Pacific/Apia", "Pacific/Kiritimati")),
    ]

    def test_examples(self):
        # Python < 3.4 compatibility:
        if not hasattr(self, "subTest"):
            self.skipTest("No subTest support")

        for (js_offset_hours, expected_tzs) in self.example_offsets_timezones:
            with self.subTest(hour=js_offset_hours):
                js_offset_minutes = js_offset_hours * 60
                actual_tzs = (
                    str(
                        offset_to_timezone(
                            js_offset_minutes, datetime(2018, 1, 1, 0, 0, 0)
                        )
                    ),  # Start/end of year
                    str(
                        offset_to_timezone(
                            js_offset_minutes, datetime(2018, 7, 1, 0, 0, 0)
                        )
                    ),  # Mid-year
                )
                self.assertEqual(expected_tzs, actual_tzs)

    summer = datetime(2013, 6, 15, 12, 0, 0)
    winter = datetime(2013, 12, 15, 12, 0, 0)

    # Tests for various cities for both regular and daylight saving time
    def test_london_winter(self):
        tz = offset_to_timezone(0, now=self.winter)
        self.assertEqual(str(tz), "Europe/London")

    def test_london_summer(self):
        tz = offset_to_timezone(-60, now=self.summer)
        self.assertEqual(str(tz), "Europe/London")

    def test_new_york_winter(self):
        tz = offset_to_timezone(5 * 60, now=self.winter)
        self.assertEqual(str(tz), "America/New_York")

    def test_new_york_summer(self):
        tz = offset_to_timezone(4 * 60, now=self.summer)
        self.assertEqual(str(tz), "America/New_York")

    def test_tokyo(self):
        tz = offset_to_timezone(-9 * 60, now=self.summer)
        self.assertEqual(str(tz), "Asia/Tokyo")

    def test_fuzzy(self):
        """Test the fuzzy matching of timezones"""
        tz = offset_to_timezone(-10, now=self.winter)
        self.assertEqual(str(tz), "Europe/London")


class ConvertHeaderNameTestCase(TestCase):
    """Test for `templatetags.tz_detect.convert_header_name`

    This util converts django header name to suitable for AJAX request
    """

    def test_default_header_name(self):
        # default value for settings.CSRF_HEADER_NAME
        setting = "HTTP_X_CSRFTOKEN"
        result = convert_header_name(setting)
        self.assertEqual(result, "x-csrftoken")

    def test_custom_header_name(self):
        setting = "HTTP_X_XSRF_TOKEN"
        result = convert_header_name(setting)
        self.assertEqual(result, "x-xsrf-token")

    def test_custom_header_without_http_prefix(self):
        setting = "X_XSRF_TOKEN"
        result = convert_header_name(setting)
        self.assertEqual(result, "x-xsrf-token")


class TemplatetagTestCase(TestCase):
    def test_no_request_context(self):
        try:
            tz_detect({})
        except KeyError as e:
            if e.message == "request":
                self.fail("Templatetag shouldn't expect request in context.")
            else:
                raise
