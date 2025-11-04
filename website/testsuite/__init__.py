# website/testsuite/__init__.py

import unittest

from django.test.runner import DiscoverRunner


class WebsiteDiscoverRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        suite = super().build_suite(test_labels, extra_tests=extra_tests, **kwargs)

        # Also include standalone test_*.py files under website/
        loader = unittest.defaultTestLoader
        for modname in [
            "test_api",
            "test_badge_views",
            "test_blog",
            "test_bugs_list",
            "test_hackathon_leaderboard",
            "test_issues",
            "test_organization",
            "test_rooms",
            "test_slack",
            "test_user_profile",
            "tests",
        ]:
            try:
                module = __import__(f"website.{modname}", fromlist=["*"])
                suite.addTests(loader.loadTestsFromModule(module))
            except ModuleNotFoundError:
                pass

        return suite
