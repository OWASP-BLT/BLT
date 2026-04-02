import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import Contributor, Domain, GitHubIssue, Repo


class DarkModeTests(TestCase):
    """Test suite for dark mode functionality"""

    def setUp(self):
        self.client = Client()

    def test_set_theme_endpoint_accepts_dark(self):
        """Test that the set-theme endpoint accepts and saves dark theme"""
        response = self.client.post(
            reverse("set_theme"), data=json.dumps({"theme": "dark"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "dark")

    def test_set_theme_endpoint_accepts_light(self):
        """Test that the set-theme endpoint accepts and saves light theme"""
        response = self.client.post(
            reverse("set_theme"), data=json.dumps({"theme": "light"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "light")

    def test_set_theme_invalid_method(self):
        """Test that GET request to set-theme endpoint returns 405"""
        response = self.client.get(reverse("set_theme"))
        self.assertEqual(response.status_code, 405)

    def test_dark_mode_toggle_in_base_template(self):
        """Test that dark mode toggle is present in base template"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check for dark mode JS and CSS references (may be hashed in production)
        self.assertTrue(
            "darkMode" in response.content.decode() or "dark-mode" in response.content.decode(),
            "Dark mode script reference not found in response",
        )
        self.assertContains(response, "custom-scrollbar")

    def test_dark_mode_script_loads(self):
        """Test that dark mode JS script is included in pages"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check for dark mode related content (script tag with darkMode reference)
        content = response.content.decode()
        self.assertTrue("darkMode.js" in content or "darkMode" in content, "Dark mode script not found in response")


class StatusPageTests(TestCase):
    """Test suite for status page functionality"""

    def setUp(self):
        self.client = Client()

    def test_status_page_loads(self):
        """Test that the status page loads without errors"""
        response = self.client.get(reverse("status_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.context)

    def test_status_page_has_required_context(self):
        """Test that status page provides expected context data"""
        response = self.client.get(reverse("status_page"))
        self.assertEqual(response.status_code, 200)
        status = response.context["status"]

        # Check for essential status data keys
        self.assertIn("management_commands", status)
        self.assertIn("available_commands", status)


class TopEarnersTests(TestCase):
    """Test suite for top earners calculation on homepage"""

    def setUp(self):
        self.client = Client()

        # Patch external HTTP fetchers so tests are fast and network-independent
        self._patch_devto = patch("website.views.core.fetch_devto_articles", return_value=[])
        self._patch_job_board = patch("website.views.core.get_job_board_data", return_value=([], []))
        self._patch_discussions = patch("website.views.core.fetch_github_discussions", return_value=[])
        self._patch_devto.start()
        self._patch_job_board.start()
        self._patch_discussions.start()

        # Create test repository
        self.repo = Repo.objects.create(
            name="TestRepo", repo_url="https://github.com/test/repo", description="Test repository"
        )

        # Create test contributors
        self.contributor1 = Contributor.objects.create(
            name="testuser1",
            github_id=12345,
            github_url="https://github.com/testuser1",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            contributor_type="User",
            contributions=10,
        )

        self.contributor2 = Contributor.objects.create(
            name="testuser2",
            github_id=67890,
            github_url="https://github.com/testuser2",
            avatar_url="https://avatars.githubusercontent.com/u/67890",
            contributor_type="User",
            contributions=5,
        )

        # Create test issues with $5 label
        self.issue1 = GitHubIssue.objects.create(
            issue_id=1,
            title="Test Issue 1",
            state="closed",
            type="issue",
            has_dollar_tag=True,  # $5 label
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/test/repo/issues/1",
            repo=self.repo,
        )

        self.issue2 = GitHubIssue.objects.create(
            issue_id=2,
            title="Test Issue 2",
            state="closed",
            type="issue",
            has_dollar_tag=True,  # $5 label
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/test/repo/issues/2",
            repo=self.repo,
        )

        # Create test PRs linked to issues
        self.pr1 = GitHubIssue.objects.create(
            issue_id=101,
            title="Test PR 1",
            state="closed",
            type="pull_request",
            is_merged=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            merged_at=timezone.now(),
            url="https://github.com/test/repo/pull/101",
            repo=self.repo,
            contributor=self.contributor1,
        )

        self.pr2 = GitHubIssue.objects.create(
            issue_id=102,
            title="Test PR 2",
            state="closed",
            type="pull_request",
            is_merged=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            merged_at=timezone.now(),
            url="https://github.com/test/repo/pull/102",
            repo=self.repo,
            contributor=self.contributor1,
        )

        self.pr3 = GitHubIssue.objects.create(
            issue_id=103,
            title="Test PR 3",
            state="closed",
            type="pull_request",
            is_merged=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            merged_at=timezone.now(),
            url="https://github.com/test/repo/pull/103",
            repo=self.repo,
            contributor=self.contributor2,
        )

        # Link PRs to issues (contributor1 has 2 PRs, contributor2 has 1 PR)
        self.pr1.linked_issues.add(self.issue1)
        self.pr2.linked_issues.add(self.issue2)
        self.pr3.linked_issues.add(self.issue2)

    def tearDown(self):
        self._patch_devto.stop()
        self._patch_job_board.stop()
        self._patch_discussions.stop()

    def test_top_earners_calculation(self):
        """Test that top earners are calculated correctly based on $5 issues and linked PRs"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

        # Check if top_earners is in context
        self.assertIn("top_earners", response.context)
        top_earners = response.context["top_earners"]

        # Should have 2 earners
        self.assertEqual(len(top_earners), 2)

        # contributor1 should be first with $10 (2 PRs × $5)
        self.assertEqual(top_earners[0].user.username, "testuser1")
        self.assertEqual(float(top_earners[0].total_earnings), 10.0)

        # contributor2 should be second with $5 (1 PR × $5)
        self.assertEqual(top_earners[1].user.username, "testuser2")
        self.assertEqual(float(top_earners[1].total_earnings), 5.0)

    def test_top_earners_only_counts_merged_prs(self):
        """Test that only merged PRs are counted for earnings"""
        # Create an unmerged PR linked to a $5 issue
        unmerged_pr = GitHubIssue.objects.create(
            issue_id=104,
            title="Test PR 4 (not merged)",
            state="open",
            type="pull_request",
            is_merged=False,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/test/repo/pull/104",
            repo=self.repo,
            contributor=self.contributor1,
        )
        unmerged_pr.linked_issues.add(self.issue1)

        response = self.client.get(reverse("home"))
        top_earners = response.context["top_earners"]

        # contributor1 should still have $10 (only 2 merged PRs counted)
        contributor1_earnings = next((e for e in top_earners if e.user.username == "testuser1"), None)
        self.assertIsNotNone(contributor1_earnings)
        self.assertEqual(float(contributor1_earnings.total_earnings), 10.0)

    def test_top_earners_only_counts_dollar_five_issues(self):
        """Test that only issues with $5 label are counted"""
        # Create an issue without $5 label
        non_dollar_issue = GitHubIssue.objects.create(
            issue_id=3,
            title="Test Issue 3 (no $5 label)",
            state="closed",
            type="issue",
            has_dollar_tag=False,  # No $5 label
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/test/repo/issues/3",
            repo=self.repo,
        )

        # Create a PR linked to the non-$5 issue
        pr_for_non_dollar = GitHubIssue.objects.create(
            issue_id=105,
            title="Test PR 5",
            state="closed",
            type="pull_request",
            is_merged=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            merged_at=timezone.now(),
            url="https://github.com/test/repo/pull/105",
            repo=self.repo,
            contributor=self.contributor1,
        )
        pr_for_non_dollar.linked_issues.add(non_dollar_issue)

        response = self.client.get(reverse("home"))
        top_earners = response.context["top_earners"]

        # contributor1 should still have $10 (only $5 labeled issues counted)
        contributor1_earnings = next((e for e in top_earners if e.user.username == "testuser1"), None)
        self.assertIsNotNone(contributor1_earnings)
        self.assertEqual(float(contributor1_earnings.total_earnings), 10.0)


class SitemapTests(TestCase):
    """Test suite for sitemap functionality"""

    def setUp(self):
        self.client = Client()
        # Create test user and domain for sitemap
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.domain = Domain.objects.create(name="test.example.com", url="https://test.example.com")

    def test_sitemap_loads(self):
        """Test that the sitemap page loads without errors"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)

    def test_sitemap_context_has_username(self):
        """Test that sitemap provides random_username in context"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("random_username", response.context)
        # Should be a string, not a User object
        self.assertIsInstance(response.context["random_username"], str)

    def test_sitemap_context_has_domain(self):
        """Test that sitemap provides random_domain in context"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("random_domain", response.context)
        # Should be a string, not a Domain object
        self.assertIsInstance(response.context["random_domain"], str)

    def test_sitemap_with_no_users(self):
        """Test that sitemap handles case when no users exist"""
        User.objects.all().delete()
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        # Should have fallback value
        self.assertEqual(response.context["random_username"], "user")

    def test_sitemap_with_no_domains(self):
        """Test that sitemap handles case when no domains exist"""
        Domain.objects.all().delete()
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        # Should have fallback value
        self.assertEqual(response.context["random_domain"], "example.com")

    def test_sitemap_template_renders_urls(self):
        """Test that sitemap template contains profile and domain URLs"""
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Check that profile URL is present
        self.assertIn("profile", content)
        # Check that domain URL is present
        self.assertIn("domain", content)
        # Check that follow_user URL is present
        self.assertIn("follow", content)
