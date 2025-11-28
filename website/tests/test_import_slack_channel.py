import csv
import io
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from website.models import Project, SlackChannel


class ImportSlackChannelTests(TestCase):
    """
    Tests for the import_slack_channel management command.
    Covers SlackChannel creation, Project linking, matching logic,
    backward compatibility, and error-handling.
    """

    def setUp(self):
        # Create sample projects to match
        self.zap = Project.objects.create(name="www-project-zap", description="Test ZAP")
        self.nodegoat = Project.objects.create(name="www-project-nodegoat", description="Nodegoat test")

    def run_import_with_rows(self, rows):
        """
        Helper method:
        Creates an in-memory CSV and runs the management command on it.
        """

        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["slack_channel", "slack_id", "slack_url"])

        for row in rows:
            writer.writerow(row)

        csv_data.seek(0)

        with patch("builtins.open", return_value=csv_data):
            call_command("import_slack_channel", "--csv", "dummy.csv")

    #  SlackChannel Creation Tests

    def test_slackchannel_created_correctly(self):
        """
        Verify SlackChannel is created with correct mapping:
        slack_id → channel_id
        slack_channel → name
        slack_url → slack_url
        """
        self.run_import_with_rows([["project-zap", "C12345", "https://slack.com/ZAP"]])

        ch = SlackChannel.objects.get(channel_id="C12345")
        self.assertEqual(ch.name, "project-zap")
        self.assertEqual(ch.slack_url, "https://slack.com/ZAP")

    def test_slackchannel_update_or_create(self):
        """Verify update_or_create updates existing channel instead of duplicating."""

        # First import - creates channel
        self.run_import_with_rows([["project-zap", "C555", "https://fake1"]])

        # Second import - same ID should update
        self.run_import_with_rows([["project-zap", "C555", "https://fake2"]])

        self.assertEqual(SlackChannel.objects.count(), 1)
        self.assertEqual(SlackChannel.objects.first().slack_url, "https://fake2")

    #  Project Linking Tests

    def test_exact_case_insensitive_matching(self):
        self.run_import_with_rows([["project-zap", "CZAP", "https://slack.com/zap"]])

        ch = SlackChannel.objects.get(channel_id="CZAP")
        self.assertEqual(ch.project, self.zap)

    def test_partial_matching_logic(self):
        """
        project-nodegoat → matches www-project-nodegoat
        """
        self.run_import_with_rows([["project-nodegoat", "CNG", "https://slack.com/ng"]])

        ch = SlackChannel.objects.get(channel_id="CNG")
        self.assertEqual(ch.project, self.nodegoat)

    #  Backward Compatibility Tests
    def test_project_old_fields_still_updated(self):
        self.run_import_with_rows([["project-zap", "C999", "https://slack.com/z"]])

        p = Project.objects.get(name="www-project-zap")
        self.assertEqual(p.slack_id, "C999")
        self.assertEqual(p.slack_channel, "project-zap")
        self.assertEqual(p.slack, "https://slack.com/z")

    #  Error Handling Tests
    @patch("django.core.management.base.BaseCommand.stdout")
    def test_unmatched_project_logged(self, mocked_stdout):
        """
        When a channel can't be matched, a warning should be logged.
        """
        self.run_import_with_rows([["project-unknown", "C404", "https://nope"]])

        # SlackChannel should still be created but without project
        ch = SlackChannel.objects.get(channel_id="C404")
        self.assertIsNone(ch.project)

        # Confirm warning logged
        logged_text = "".join([call[0][0] for call in mocked_stdout.write.call_args_list])
        self.assertIn("No matching project found", logged_text)
