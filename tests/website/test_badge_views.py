import io
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from PIL import Image

from website.models import IP, Project, Repo


class BadgeViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test project
        self.project = Project.objects.create(name="Test Project", slug="test-project", project_visit_count=42)

        # Create a test repo
        self.repo = Repo.objects.create(
            name="Test Repo",
            slug="test-repo",
            repo_visit_count=42,
            project=self.project,
            repo_url="https://github.com/test/test",
        )

        # Create IP records for last 7 days
        today = now().date()
        for i in range(7):
            date = today - timezone.timedelta(days=i)
            badge_path = reverse("project-badge", kwargs={"slug": self.project.slug})
            IP.objects.create(address=f"192.168.1.{i}", path=badge_path, created=date, count=1)

    def test_project_badge_view(self):
        """Test project badge view returns correct chart with visit count"""
        url = reverse("project-badge", kwargs={"slug": self.project.slug})
        response = self.client.get(url)

        # Check response basics
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        cache_control = "no-store, no-cache, must-revalidate, max-age=0"
        self.assertEqual(response["Cache-Control"], cache_control)
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

        # Verify it's a valid PNG image
        image_data = response.content
        self.assertTrue(image_data.startswith(b"\x89PNG"))  # PNG magic number

        # Verify we can load it as a PIL image
        buf = io.BytesIO(image_data)
        try:
            Image.open(buf)
            is_valid_image = True
        except Exception:
            is_valid_image = False
        self.assertTrue(is_valid_image)

        # Check visit count increment
        self.project.refresh_from_db()
        # Should increment by 1
        self.assertEqual(self.project.project_visit_count, 43)

    def test_repo_badge_view(self):
        """Test that repo badge view returns correct chart with visit count"""
        url = reverse("repo-badge", kwargs={"slug": self.repo.slug})
        response = self.client.get(url)

        # Check response basics
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        cache_control = "no-store, no-cache, must-revalidate, max-age=0"
        self.assertEqual(response["Cache-Control"], cache_control)
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

        # Verify it's a valid PNG image
        image_data = response.content
        self.assertTrue(image_data.startswith(b"\x89PNG"))  # PNG magic number

        # Verify we can load it as a PIL image
        buf = io.BytesIO(image_data)
        try:
            Image.open(buf)
            is_valid_image = True
        except Exception:
            is_valid_image = False
        self.assertTrue(is_valid_image)

        # Check visit count increment
        self.repo.refresh_from_db()
        # Should increment by 1
        self.assertEqual(self.repo.repo_visit_count, 43)

    def test_badge_view_404(self):
        """Test that badge views return 404 for non-existent slugs"""
        # Test project badge
        url = reverse("project-badge", kwargs={"slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # Test repo badge
        url = reverse("repo-badge", kwargs={"slug": "non-existent"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_badge_view_visit_tracking(self):
        """Test that badge views properly track unique visits"""
        # First visit
        url = reverse("project-badge", kwargs={"slug": self.project.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Check IP record was created
        ip_record = IP.objects.filter(path=url).first()
        self.assertIsNotNone(ip_record)
        self.assertEqual(ip_record.count, 1)

        # Second visit on same day shouldn't increment
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        ip_record.refresh_from_db()
        self.assertEqual(ip_record.count, 1)  # Count should stay the same

        # Simulate next day visit
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now() + timezone.timedelta(days=1)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

            # Should create new record for new day
            self.assertEqual(
                IP.objects.filter(path=url).count(),
                8,  # 7 from setup + 2 from test
            )

    def test_badge_view_historical_data(self):
        """Test that badge view shows historical visit data correctly"""
        url = reverse("project-badge", kwargs={"slug": self.project.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify response is a PNG image
        self.assertEqual(response["Content-Type"], "image/png")
        image_data = response.content
        self.assertTrue(image_data.startswith(b"\x89PNG"))

        # Check we have the expected number of historical records
        seven_days_ago = now().date() - timezone.timedelta(days=7)
        visit_count = IP.objects.filter(path=url, created__date__gte=seven_days_ago).count()
        # 7 from setup + 1 from this test
        self.assertEqual(visit_count, 8)
