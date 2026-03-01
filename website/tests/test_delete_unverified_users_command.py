from datetime import timedelta
from io import StringIO

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone


class DeleteUnverifiedUsersCommandTestCase(TestCase):
    def setUp(self):
        old_date = timezone.now() - timedelta(days=60)

        self.verified_user = User.objects.create_user(
            username="verified_user",
            email="verified@example.com",
            password="testpass123",
        )
        EmailAddress.objects.create(
            user=self.verified_user,
            email=self.verified_user.email,
            verified=True,
            primary=True,
        )

        self.unverified_user = User.objects.create_user(
            username="unverified_user",
            email="unverified@example.com",
            password="testpass123",
        )
        EmailAddress.objects.create(
            user=self.unverified_user,
            email=self.unverified_user.email,
            verified=False,
            primary=True,
        )

        self.unverified_no_record = User.objects.create_user(
            username="no_record_user",
            email="norecord@example.com",
            password="testpass123",
        )

        self.recent_unverified = User.objects.create_user(
            username="recent_user",
            email="recent@example.com",
            password="testpass123",
        )
        EmailAddress.objects.create(
            user=self.recent_unverified,
            email=self.recent_unverified.email,
            verified=False,
            primary=True,
        )

        self.staff_unverified = User.objects.create_user(
            username="staff_user",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        EmailAddress.objects.create(
            user=self.staff_unverified,
            email=self.staff_unverified.email,
            verified=False,
            primary=True,
        )

        for user in [
            self.verified_user,
            self.unverified_user,
            self.unverified_no_record,
            self.staff_unverified,
        ]:
            User.objects.filter(id=user.id).update(date_joined=old_date)

    def test_dry_run_is_default_and_does_not_delete(self):
        out = StringIO()
        call_command("delete_unverified_users", "--days=30", stdout=out)

        output = out.getvalue()
        self.assertIn("Mode: DRY-RUN", output)
        self.assertIn("unverified_user", output)
        self.assertIn("no_record_user", output)
        self.assertIn("Dry-run only", output)

        self.assertTrue(User.objects.filter(username="unverified_user").exists())
        self.assertTrue(User.objects.filter(username="no_record_user").exists())

    def test_execute_deletes_only_matching_non_staff_users(self):
        out = StringIO()
        call_command("delete_unverified_users", "--days=30", "--execute", stdout=out)

        output = out.getvalue()
        self.assertIn("Mode: EXECUTE", output)
        self.assertIn("Deleted 2 user(s).", output)

        self.assertTrue(User.objects.filter(username="verified_user").exists())
        self.assertFalse(User.objects.filter(username="unverified_user").exists())
        self.assertFalse(User.objects.filter(username="no_record_user").exists())
        self.assertTrue(User.objects.filter(username="recent_user").exists())
        self.assertTrue(User.objects.filter(username="staff_user").exists())

    def test_limit_applies_to_candidates(self):
        out = StringIO()
        call_command("delete_unverified_users", "--days=30", "--execute", "--limit=1", stdout=out)

        self.assertIn("Deleted 1 user(s).", out.getvalue())

        remaining = User.objects.filter(username__in=["unverified_user", "no_record_user"]).count()
        self.assertEqual(remaining, 1)

    def test_include_staff_flag_allows_staff_deletion(self):
        out = StringIO()
        call_command(
            "delete_unverified_users",
            "--days=30",
            "--execute",
            "--include-staff",
            stdout=out,
        )

        self.assertIn("Deleted 3 user(s).", out.getvalue())
        self.assertFalse(User.objects.filter(username="staff_user").exists())
