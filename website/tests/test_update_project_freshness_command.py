"""
Tests for the update_project_freshness management command.
"""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from website.models import Organization, Project, Repo


class UpdateProjectFreshnessCommandTestCase(TestCase):
    """Test cases for update_project_freshness management command"""

    def setUp(self):
        """Set up test data"""
        self.org = Organization.objects.create(name="Test Org", url="https://test.org")
        self.now = timezone.now()

    def test_command_updates_all_projects(self):
        """Test that command updates freshness for all projects"""
        # Create projects with different activity levels
        project1 = Project.objects.create(
            name="Active Project", organization=self.org, url="https://github.com/test/active"
        )
        Repo.objects.create(
            project=project1,
            name="active-repo",
            repo_url="https://github.com/test/active-repo",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=2),
        )

        project2 = Project.objects.create(
            name="Inactive Project", organization=self.org, url="https://github.com/test/inactive"
        )
        Repo.objects.create(
            project=project2,
            name="old-repo",
            repo_url="https://github.com/test/old-repo",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=100),
        )

        project3 = Project.objects.create(
            name="No Repos Project", organization=self.org, url="https://github.com/test/empty"
        )

        # Run command
        out = StringIO()
        call_command("update_project_freshness", stdout=out)

        # Verify all projects were updated
        project1.refresh_from_db()
        project2.refresh_from_db()
        project3.refresh_from_db()

        self.assertGreater(project1.freshness, 0.0)
        self.assertEqual(project2.freshness, 0.0)
        self.assertEqual(project3.freshness, 0.0)

        # Check output
        output = out.getvalue()
        self.assertIn("Starting freshness update", output)
        self.assertIn("Processed: 3", output)
        self.assertIn("Errors: 0", output)
        self.assertIn("Freshness update completed", output)

    def test_command_handles_errors_gracefully(self):
        """Test that command handles individual project errors without stopping"""
        project1 = Project.objects.create(
            name="Good Project", organization=self.org, url="https://github.com/test/good"
        )
        Repo.objects.create(
            project=project1,
            name="good-repo",
            repo_url="https://github.com/test/good-repo",
            is_archived=False,
            last_commit_date=self.now - timedelta(days=5),
        )

        project2 = Project.objects.create(
            name="Error Project", organization=self.org, url="https://github.com/test/error"
        )

        out = StringIO()
        err = StringIO()

        # Mock calculate_freshness to raise error for one project
        original_calculate = Project.calculate_freshness

        def mock_calculate(self):
            if self.name == "Error Project":
                raise ValueError("Test error")
            return original_calculate(self)

        with patch.object(Project, "calculate_freshness", mock_calculate):
            call_command("update_project_freshness", stdout=out, stderr=err)

        # Check that good project was updated
        project1.refresh_from_db()
        self.assertEqual(float(project1.freshness), 5.0)

        # Check error was logged
        error_output = err.getvalue()
        self.assertIn(f"[ERROR] Project ID {project2.id}", error_output)
        self.assertIn("Test error", error_output)

        # Check summary shows 1 error
        output = out.getvalue()
        self.assertIn("Processed: 1", output)
        self.assertIn("Errors: 1", output)

    def test_command_execution_time_reported(self):
        """Test that command reports execution time"""
        Project.objects.create(name="Test Project", organization=self.org, url="https://github.com/test/project")

        out = StringIO()
        call_command("update_project_freshness", stdout=out)

        output = out.getvalue()
        self.assertIn("Execution time:", output)
        self.assertIn("s", output)  # Should have 's' for seconds

    def test_command_with_zero_projects(self):
        """Test command behavior when there are no projects"""
        out = StringIO()
        call_command("update_project_freshness", stdout=out)

        output = out.getvalue()
        self.assertIn("Starting freshness update for 0 projects", output)
        self.assertIn("Processed: 0", output)
        self.assertIn("Errors: 0", output)
