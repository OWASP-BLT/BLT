"""Tests for hackathon form functionality."""

import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from website.forms import HackathonForm
from website.models import Organization, Repo


class HackathonFormTestCase(TestCase):
    """Test case for the hackathon form."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Create organization with user as admin
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            url="https://example.com",
            admin=self.user,
        )

        # Create existing repository
        self.existing_repo = Repo.objects.create(
            name="Existing Repo",
            slug="existing-repo",
            repo_url="https://github.com/test/existing",
            organization=self.organization,
        )

        # Set up form data
        now = timezone.now()
        self.form_data = {
            "name": "Test Hackathon",
            "description": "A test hackathon",
            "organization": self.organization.id,
            "start_time": (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "end_time": (now + datetime.timedelta(days=8)).strftime("%Y-%m-%dT%H:%M"),
            "registration_open": True,
            "repositories": [self.existing_repo.id],
        }

    def test_form_with_valid_data(self):
        """Test form with valid data."""
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_with_new_repo_urls(self):
        """Test form with new repository URLs."""
        self.form_data["new_repo_urls"] = "https://github.com/owner/repo1\nhttps://github.com/owner/repo2"
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_with_invalid_repo_url(self):
        """Test form with invalid repository URL."""
        self.form_data["new_repo_urls"] = "https://gitlab.com/owner/repo"
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("new_repo_urls", form.errors)

    def test_form_with_malformed_repo_url(self):
        """Test form with malformed repository URL."""
        self.form_data["new_repo_urls"] = "https://github.com/incomplete"
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("new_repo_urls", form.errors)

    def test_form_creates_new_repositories(self):
        """Test that form creates new repositories when saved."""
        self.form_data["new_repo_urls"] = "https://github.com/owner/newrepo1\nhttps://github.com/owner/newrepo2"
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

        # Save the form
        hackathon = form.save()

        # Check that new repositories were created
        new_repo1 = Repo.objects.filter(repo_url="https://github.com/owner/newrepo1").first()
        new_repo2 = Repo.objects.filter(repo_url="https://github.com/owner/newrepo2").first()

        self.assertIsNotNone(new_repo1)
        self.assertIsNotNone(new_repo2)
        self.assertEqual(new_repo1.name, "newrepo1")
        self.assertEqual(new_repo2.name, "newrepo2")
        self.assertEqual(new_repo1.organization, self.organization)
        self.assertEqual(new_repo2.organization, self.organization)

        # Check that repositories are linked to hackathon
        self.assertIn(new_repo1, hackathon.repositories.all())
        self.assertIn(new_repo2, hackathon.repositories.all())
        self.assertIn(self.existing_repo, hackathon.repositories.all())

    def test_form_handles_existing_repo_url(self):
        """Test that form handles existing repository URLs correctly."""
        self.form_data["new_repo_urls"] = f"{self.existing_repo.repo_url}\nhttps://github.com/owner/newrepo"
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

        # Save the form
        hackathon = form.save()

        # Should not create duplicate of existing repo
        repos_with_url = Repo.objects.filter(repo_url=self.existing_repo.repo_url)
        self.assertEqual(repos_with_url.count(), 1)

        # Should create the new repo
        new_repo = Repo.objects.filter(repo_url="https://github.com/owner/newrepo").first()
        self.assertIsNotNone(new_repo)

        # Both should be linked to hackathon
        self.assertIn(self.existing_repo, hackathon.repositories.all())
        self.assertIn(new_repo, hackathon.repositories.all())

    def test_form_without_new_repo_urls(self):
        """Test form without new repository URLs."""
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

        hackathon = form.save()
        self.assertEqual(hackathon.repositories.count(), 1)
        self.assertIn(self.existing_repo, hackathon.repositories.all())

    def test_form_filters_organizations(self):
        """Test that form only shows organizations where user is admin or manager."""
        # Create another organization without the user
        other_org = Organization.objects.create(
            name="Other Organization",
            slug="other-org",
            url="https://other.com",
        )

        form = HackathonForm(user=self.user)
        org_queryset = form.fields["organization"].queryset

        # Should only include organization where user is admin
        self.assertIn(self.organization, org_queryset)
        self.assertNotIn(other_org, org_queryset)

    def test_form_empty_new_repo_urls(self):
        """Test form with empty new_repo_urls field."""
        self.form_data["new_repo_urls"] = ""
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_form_new_repo_urls_with_blank_lines(self):
        """Test form with blank lines in new_repo_urls."""
        self.form_data["new_repo_urls"] = "https://github.com/owner/repo1\n\n\nhttps://github.com/owner/repo2\n"
        form = HackathonForm(data=self.form_data, user=self.user)
        self.assertTrue(form.is_valid())

        # Should only create 2 repos, ignoring blank lines
        hackathon = form.save()
        new_repos = Repo.objects.filter(
            repo_url__in=["https://github.com/owner/repo1", "https://github.com/owner/repo2"]
        )
        self.assertEqual(new_repos.count(), 2)
