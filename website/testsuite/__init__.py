# website/testsuite/__init__.py

import importlib
import logging
import os
import unittest

from django.test.runner import DiscoverRunner

logger = logging.getLogger(__name__)


class WebsiteDiscoverRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        suite = super().build_suite(test_labels, extra_tests=extra_tests, **kwargs)

        # Also include standalone test_*.py files under website/
        loader = unittest.defaultTestLoader

        # Dynamically discover test modules
        website_dir = os.path.dirname(os.path.dirname(__file__))
        for filename in os.listdir(website_dir):
            if filename.startswith("test_") and filename.endswith(".py"):
                modname = filename[:-3]  # Remove .py extension
            elif filename == "tests.py":
                modname = "tests"
            else:
                continue

            try:
                module = importlib.import_module(f"website.{modname}")
                suite.addTests(loader.loadTestsFromModule(module))
            except ModuleNotFoundError:
                logger.debug(f"Test module website.{modname} not found, skipping")

        return suite
