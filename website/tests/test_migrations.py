"""
Tests to ensure database migrations are properly managed.

This module contains tests that verify:
1. No migration conflicts exist (duplicate migration numbers requiring merge)
2. All migrations can be applied successfully
"""

from django.core.management import call_command
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase


class MigrationConflictTestCase(TestCase):
    """Test case to detect migration conflicts that would require merge migrations."""

    def test_no_migration_conflicts(self):
        """
        Test that there are no migration conflicts in the codebase.

        Migration conflicts occur when two branches independently create migrations
        with the same number (e.g., both create 0100_something.py). This test uses
        Django's MigrationLoader to detect such conflicts, which would require
        creating a merge migration to resolve.

        This test will fail if:
        - Two migrations with the same number exist in the same app
        - Migrations have conflicting dependencies that can't be resolved
        """
        loader = MigrationLoader(None)
        conflicts = loader.detect_conflicts()

        # If conflicts exist, build a helpful error message
        if conflicts:
            error_msg = ["Migration conflicts detected that require merge migrations:"]
            for app_label, migration_names in conflicts.items():
                error_msg.append(f"\nApp '{app_label}' has conflicting migrations:")
                for name in migration_names:
                    error_msg.append(f"  - {name}")
                error_msg.append(f"\nTo resolve, run: python manage.py makemigrations --merge {app_label}")

            self.fail("\n".join(error_msg))

    def test_migrations_can_be_applied(self):
        """
        Test that all migrations can be applied without errors.

        This test runs 'migrate --check' which verifies that:
        1. All migrations are properly structured
        2. No unapplied migrations exist (they should all be applied during test setup)
        3. The migration graph is consistent

        Note: Django test framework automatically applies all migrations before
        running tests, so this mainly serves as a sanity check.
        """
        try:
            # --check flag makes migrate exit with non-zero status if there are
            # unapplied migrations, without actually applying them
            call_command("migrate", "--check", verbosity=0)
        except SystemExit as e:
            if e.code != 0:
                self.fail(
                    "Migrations check failed. There may be unapplied migrations " "or issues with the migration graph."
                )
