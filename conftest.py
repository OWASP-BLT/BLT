"""
Pytest configuration for BLT tests.

This file ensures that Django settings are properly configured for testing.
"""
import os
import sys

import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings before running tests."""
    # Ensure Django is set up
    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
        django.setup()


def pytest_collection_modifyitems(config, items):
    """
    Add Django DB marker to all tests that need database access.
    This ensures tests use the test database.
    """
    for item in items:
        if "django_db" not in item.keywords:
            # Add django_db marker to all tests
            item.add_marker("django_db")
