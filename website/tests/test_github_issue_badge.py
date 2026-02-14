from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from website.models import IP, GitHubIssue, Repo

BADGE_KWARGS = {"owner": "owner", "repo_name": "test-repo", "issue_id": 42}
BADGE_KWARGS_NO_BOUNTY = {"owner": "owner", "repo_name": "test-repo", "issue_id": 99}
BADGE_KWARGS_MISSING = {"owner": "owner", "repo_name": "test-repo", "issue_id": 999999}


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class GitHubIssueBadgeTests(TestCase):
    """Comprehensive tests for the GitHubIssueBadgeView endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.repo = Repo.objects.create(
            name="test-repo",
            slug="owner-test-repo",
            repo_url="https://github.com/owner/test-repo",
        )
        cls.issue = GitHubIssue.objects.create(
            issue_id=42,
            title="Test issue",
            body="Some body",
            state="open",
            type="issue",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/owner/test-repo/issues/42",
            repo=cls.repo,
            p2p_amount_usd=Decimal("50.00"),
        )
        cls.issue_no_bounty = GitHubIssue.objects.create(
            issue_id=99,
            title="No bounty issue",
            body="",
            state="open",
            type="issue",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/owner/test-repo/issues/99",
            repo=cls.repo,
            p2p_amount_usd=None,
        )

    def setUp(self):
        self.client = Client()
        # Clear cache between tests
        from django.core.cache import cache

        cache.clear()

    # ------------------------------------------------------------------
    # 1. Basic SVG response
    # ------------------------------------------------------------------
    def test_badge_returns_svg(self):
        """Badge endpoint returns image/svg+xml content type."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")

    # ------------------------------------------------------------------
    # 2. SVG contains brand color
    # ------------------------------------------------------------------
    def test_badge_contains_brand_color(self):
        """SVG output contains the BLT brand color #e74c3c."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        self.assertIn("#e74c3c", response.content.decode())

    # ------------------------------------------------------------------
    # 3. Badge shows bounty amount
    # ------------------------------------------------------------------
    def test_badge_shows_bounty(self):
        """Badge includes the bounty dollar amount when set."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        content = response.content.decode()
        self.assertIn("$50.00", content)

    # ------------------------------------------------------------------
    # 4. Zero-bounty badge shows $0.00
    # ------------------------------------------------------------------
    def test_badge_zero_bounty(self):
        """Badge shows $0.00 when no bounty is set."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS_NO_BOUNTY)
        response = self.client.get(url)
        content = response.content.decode()
        self.assertIn("$0.00", content)

    # ------------------------------------------------------------------
    # 5. Non-existent issue returns badge with zeros
    # ------------------------------------------------------------------
    def test_badge_nonexistent_issue(self):
        """Badge still returns a valid SVG for an unknown issue_id."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS_MISSING)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        content = response.content.decode()
        # Should show 0 views and $0.00
        self.assertIn(">0<", content)
        self.assertIn("$0.00", content)

    # ------------------------------------------------------------------
    # 6. Cache headers present
    # ------------------------------------------------------------------
    def test_badge_cache_headers(self):
        """Response includes Cache-Control with max-age=300."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        self.assertIn("max-age=300", response["Cache-Control"])

    # ------------------------------------------------------------------
    # 7. ETag header present
    # ------------------------------------------------------------------
    def test_badge_etag_header(self):
        """Response includes an ETag header."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        self.assertIn("ETag", response)
        self.assertTrue(len(response["ETag"]) > 0)

    # ------------------------------------------------------------------
    # 8. Conditional request returns 304
    # ------------------------------------------------------------------
    def test_badge_conditional_304(self):
        """Sending If-None-Match with the correct ETag yields 304."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        first = self.client.get(url)
        etag = first["ETag"]
        second = self.client.get(url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(second.status_code, 304)

    # ------------------------------------------------------------------
    # 9. IP tracking on badge request
    # ------------------------------------------------------------------
    def test_badge_tracks_ip(self):
        """Badge endpoint creates an IP record for the visitor."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        ip_before = IP.objects.filter(path=url).count()
        self.client.get(url)
        ip_after = IP.objects.filter(path=url).count()
        self.assertEqual(ip_after, ip_before + 1)

    # ------------------------------------------------------------------
    # 10. Duplicate IP same day is not created
    # ------------------------------------------------------------------
    def test_badge_no_duplicate_ip_same_day(self):
        """Second request from same IP on same day does not create a new IP record."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        self.client.get(url)
        count_after_first = IP.objects.filter(path=url).count()
        self.client.get(url)
        count_after_second = IP.objects.filter(path=url).count()
        self.assertEqual(count_after_first, count_after_second)

    # ------------------------------------------------------------------
    # 11. View count reflects detail-page visits (not badge visits)
    # ------------------------------------------------------------------
    def test_badge_counts_detail_page_views(self):
        """View count in badge is based on detail-page IP records, not badge hits."""
        detail_path = f"/github-issues/{self.issue.pk}/"
        # Seed 3 unique detail-page visits
        for i in range(3):
            IP.objects.create(
                address=f"10.0.0.{i}",
                path=detail_path,
                created=timezone.now(),
                count=1,
            )

        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        content = response.content.decode()
        # The views value should be "3"
        self.assertIn(">3<", content)

    # ------------------------------------------------------------------
    # 12. Only last-30-day views counted
    # ------------------------------------------------------------------
    def test_badge_excludes_old_views(self):
        """IP records older than 30 days are excluded from the view count."""
        detail_path = f"/github-issues/{self.issue.pk}/"
        # Recent visit
        IP.objects.create(
            address="10.0.0.1",
            path=detail_path,
            count=1,
        )
        # Old visit (40 days ago)
        old_date = timezone.now() - timedelta(days=40)
        old_ip = IP.objects.create(
            address="10.0.0.2",
            path=detail_path,
            count=1,
        )
        # auto_now_add ignores the value passed to create(), so update via DB
        IP.objects.filter(pk=old_ip.pk).update(created=old_date)

        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        content = response.content.decode()
        # Only the recent visit should be counted
        self.assertIn(">1<", content)

    # ------------------------------------------------------------------
    # 13. Valid SVG structure
    # ------------------------------------------------------------------
    def test_badge_valid_svg(self):
        """Badge output starts with <svg and closes with </svg>."""
        url = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        response = self.client.get(url)
        content = response.content.decode()
        self.assertTrue(content.startswith("<svg"))
        self.assertTrue(content.strip().endswith("</svg>"))

    # ------------------------------------------------------------------
    # 14. Cross-repo disambiguation – same issue_id in two repos
    # ------------------------------------------------------------------
    def test_badge_disambiguates_repos(self):
        """Badge returns the correct bounty when the same issue_id exists in two repos."""
        other_repo = Repo.objects.create(
            name="other-repo",
            slug="other-owner-other-repo",
            repo_url="https://github.com/other-owner/other-repo",
        )
        GitHubIssue.objects.create(
            issue_id=42,
            title="Same number, different repo",
            body="",
            state="open",
            type="issue",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/other-owner/other-repo/issues/42",
            repo=other_repo,
            p2p_amount_usd=Decimal("999.00"),
        )

        # Badge for original repo should still show $50.00
        url_original = reverse("github_issue_badge", kwargs=BADGE_KWARGS)
        resp_original = self.client.get(url_original)
        self.assertIn("$50.00", resp_original.content.decode())

        from django.core.cache import cache

        cache.clear()

        # Badge for other repo should show $999.00
        url_other = reverse(
            "github_issue_badge",
            kwargs={"owner": "other-owner", "repo_name": "other-repo", "issue_id": 42},
        )
        resp_other = self.client.get(url_other)
        self.assertIn("$999.00", resp_other.content.decode())
