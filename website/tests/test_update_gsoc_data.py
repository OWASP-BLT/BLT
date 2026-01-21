from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase


class UpdateGsocDataCommandTests(TestCase):
    """Tests for the update_gsoc_data management command"""

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_prs_fetched_before_reviews(self, mock_call_command):
        """Test that update_gsoc_data calls fetch_gsoc_prs before fetch_pr_reviews"""
        out = StringIO()
        call_command("update_gsoc_data", stdout=out)

        # Verify both commands were called
        self.assertEqual(mock_call_command.call_count, 2, "Should call exactly 2 commands")

        # Verify ordering: fetch_gsoc_prs first, then fetch_pr_reviews
        first_call = mock_call_command.call_args_list[0]
        second_call = mock_call_command.call_args_list[1]

        self.assertEqual(first_call[0][0], "fetch_gsoc_prs", "First command should be fetch_gsoc_prs")
        self.assertEqual(second_call[0][0], "fetch_pr_reviews", "Second command should be fetch_pr_reviews")

        # Verify success message
        output = out.getvalue()
        self.assertIn("Successfully fetched PRs", output)
        self.assertIn("Successfully fetched reviews", output)
        self.assertIn("All operations completed successfully", output)

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_skip_prs_flag_skips_pr_fetch(self, mock_call_command):
        """Test --skip-prs flag only runs fetch_pr_reviews"""
        out = StringIO()
        call_command("update_gsoc_data", "--skip-prs", stdout=out)

        # Verify only fetch_pr_reviews was called
        self.assertEqual(mock_call_command.call_count, 1, "Should call only 1 command")
        self.assertEqual(
            mock_call_command.call_args_list[0][0][0], "fetch_pr_reviews", "Should only call fetch_pr_reviews"
        )

        # Verify skip message
        output = out.getvalue()
        self.assertIn("Skipping PR fetch", output)

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_skip_reviews_flag_skips_review_fetch(self, mock_call_command):
        """Test --skip-reviews flag only runs fetch_gsoc_prs"""
        out = StringIO()
        call_command("update_gsoc_data", "--skip-reviews", stdout=out)

        # Verify only fetch_gsoc_prs was called
        self.assertEqual(mock_call_command.call_count, 1, "Should call only 1 command")
        self.assertEqual(
            mock_call_command.call_args_list[0][0][0], "fetch_gsoc_prs", "Should only call fetch_gsoc_prs"
        )

        # Verify skip message
        output = out.getvalue()
        self.assertIn("Skipping review fetch", output)

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_pr_fetch_failure_continues_to_reviews(self, mock_call_command):
        """Test that update_gsoc_data continues to reviews even if PR fetch fails"""

        def side_effect(command_name, *args, **kwargs):
            if command_name == "fetch_gsoc_prs":
                raise Exception("API rate limit exceeded")
            # fetch_pr_reviews succeeds
            return None

        mock_call_command.side_effect = side_effect

        out = StringIO()
        # Should not raise exception despite PR fetch failure
        call_command("update_gsoc_data", stdout=out)

        # Verify both commands were attempted
        self.assertEqual(mock_call_command.call_count, 2, "Should attempt both commands")

        # Verify error was logged
        output = out.getvalue()
        self.assertIn("Error fetching PRs", output)
        self.assertIn("Partial success", output)

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_review_fetch_failure_handled_gracefully(self, mock_call_command):
        """Test that update_gsoc_data reports error if review fetch fails"""

        def side_effect(command_name, *args, **kwargs):
            if command_name == "fetch_pr_reviews":
                raise Exception("Network timeout")
            # fetch_gsoc_prs succeeds
            return None

        mock_call_command.side_effect = side_effect

        out = StringIO()
        # Should not raise exception despite review fetch failure
        call_command("update_gsoc_data", stdout=out)

        # Verify both commands were called
        self.assertEqual(mock_call_command.call_count, 2, "Should call both commands")

        # Verify error was logged
        output = out.getvalue()
        self.assertIn("Successfully fetched PRs", output)
        self.assertIn("Error fetching reviews", output)
        self.assertIn("Partial success", output)

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_both_commands_failure_raises_exception(self, mock_call_command):
        """Test that update_gsoc_data raises exception when both operations fail"""

        def side_effect(command_name, *args, **kwargs):
            raise Exception(f"{command_name} failed")

        mock_call_command.side_effect = side_effect

        out = StringIO()
        # Should raise exception when both fail
        with self.assertRaises(Exception) as cm:
            call_command("update_gsoc_data", stdout=out)

        self.assertIn("GSoC data refresh failed", str(cm.exception))

        # Verify both commands were attempted
        self.assertEqual(mock_call_command.call_count, 2, "Should attempt both commands")

        # Verify error message
        output = out.getvalue()
        self.assertIn("Both operations failed", output)

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_verbose_flag_passed_to_child_commands(self, mock_call_command):
        """Test --verbose flag is passed to child commands"""
        out = StringIO()
        call_command("update_gsoc_data", "--verbose", stdout=out)

        # Verify both commands were called with verbose=True
        self.assertEqual(mock_call_command.call_count, 2, "Should call 2 commands")

        for call in mock_call_command.call_args_list:
            call_kwargs = call[1]
            self.assertTrue(call_kwargs.get("verbose"), "verbose flag should be passed to child commands")

    `@patch`("website.management.commands.update_gsoc_data.call_command")
    def test_success_output_includes_both_phases(self, mock_call_command):
        """Test successful execution shows output for both phases"""
        out = StringIO()
        call_command("update_gsoc_data", stdout=out)

        output = out.getvalue()

        # Verify phase indicators
        self.assertIn("Step 1/2: Fetching GSoC pull requests", output)
        self.assertIn("Step 2/2: Fetching PR reviews", output)

        # Verify completion summary
        self.assertIn("GSoC data refresh completed", output)
        self.assertIn("PRs: ✓", output)
        self.assertIn("Reviews: ✓", output)
