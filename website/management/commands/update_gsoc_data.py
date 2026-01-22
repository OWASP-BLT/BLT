from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

class UpdateGsocDataCommandTests(TestCase):
    """Tests for the update_gsoc_data management command."""

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_prs_fetched_before_reviews(self, mock_call_command):
        """update_gsoc_data calls fetch_gsoc_prs before fetch_pr_reviews."""
        out = StringIO()
        call_command("update_gsoc_data", stdout=out)

        # Verify two calls and ordering
        self.assertEqual(mock_call_command.call_count, 2)
        first_call = mock_call_command.call_args_list[0]
        second_call = mock_call_command.call_args_list[1]
        self.assertEqual(first_call[0][0], "fetch_gsoc_prs")
        self.assertEqual(second_call[0][0], "fetch_pr_reviews")

        # Success messages
        output = out.getvalue()
        self.assertIn("Successfully fetched PRs", output)
        self.assertIn("Successfully fetched reviews", output)
        self.assertIn("All operations completed successfully", output)

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_skip_prs_flag_skips_pr_fetch(self, mock_call_command):
        """--skip-prs runs only fetch_pr_reviews."""
        out = StringIO()
        call_command("update_gsoc_data", "--skip-prs", stdout=out)

        self.assertEqual(mock_call_command.call_count, 1)
        self.assertEqual(
            mock_call_command.call_args_list[0][0][0], "fetch_pr_reviews"
        )

        output = out.getvalue()
        self.assertIn("Skipping PR fetch", output)

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_skip_reviews_flag_skips_review_fetch(self, mock_call_command):
        """--skip-reviews runs only fetch_gsoc_prs."""
        out = StringIO()
        call_command("update_gsoc_data", "--skip-reviews", stdout=out)

        self.assertEqual(mock_call_command.call_count, 1)
        self.assertEqual(mock_call_command.call_args_list[0][0][0], "fetch_gsoc_prs")

        output = out.getvalue()
        self.assertIn("Skipping review fetch", output)

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_pr_fetch_failure_continues_to_reviews(self, mock_call_command):
        """If PR fetch fails, continue to reviews and report partial success."""

        def side_effect(command_name, *args, **kwargs):
            if command_name == "fetch_gsoc_prs":
                raise Exception("API rate limit exceeded")
            return None

        mock_call_command.side_effect = side_effect

        out = StringIO()
        call_command("update_gsoc_data", stdout=out)

        self.assertEqual(mock_call_command.call_count, 2)

        output = out.getvalue()
        self.assertIn("Error fetching PRs", output)
        self.assertIn("Partial success", output)

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_review_fetch_failure_handled_gracefully(self, mock_call_command):
        """If review fetch fails, report partial success while PRs succeeded."""

        def side_effect(command_name, *args, **kwargs):
            if command_name == "fetch_pr_reviews":
                raise Exception("Network timeout")
            return None

        mock_call_command.side_effect = side_effect

        out = StringIO()
        call_command("update_gsoc_data", stdout=out)

        self.assertEqual(mock_call_command.call_count, 2)

        output = out.getvalue()
        self.assertIn("Successfully fetched PRs", output)
        self.assertIn("Error fetching reviews", output)
        self.assertIn("Partial success", output)

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_both_commands_failure_raises_exception(self, mock_call_command):
        """If both steps fail, an exception is raised."""

        def side_effect(command_name, *args, **kwargs):
            raise Exception(f"{command_name} failed")

        mock_call_command.side_effect = side_effect

        out = StringIO()
        with self.assertRaises(Exception) as cm:
            call_command("update_gsoc_data", stdout=out)

        self.assertIn("GSoC data refresh failed", str(cm.exception))
        self.assertEqual(mock_call_command.call_count, 2)

        output = out.getvalue()
        self.assertIn("Both operations failed", output)

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_verbose_flag_passed_to_child_commands(self, mock_call_command):
        """--verbose is forwarded to child commands."""
        out = StringIO()
        call_command("update_gsoc_data", "--verbose", stdout=out)

        self.assertEqual(mock_call_command.call_count, 2)
        for _, kwargs in mock_call_command.call_args_list:
            self.assertTrue(
                kwargs.get("verbose"),
                "verbose flag should be passed to child commands",
            )

    @patch("website.management.commands.update_gsoc_data.call_command")
    def test_success_output_includes_both_phases(self, mock_call_command):
        """Successful execution prints both phases and final summary."""
        out = StringIO()
        call_command("update_gsoc_data", stdout=out)

        output = out.getvalue()
        self.assertIn("Step 1/2: Fetching GSoC pull requests", output)
        self.assertIn("Step 2/2: Fetching PR reviews", output)
        self.assertIn("GSoC data refresh completed", output)
        self.assertIn("PRs: ✓", output)
        self.assertIn("Reviews: ✓", output)
