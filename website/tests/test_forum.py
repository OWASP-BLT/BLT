from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from website.models import ForumCategory, ForumPost


class ForumViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="pass12345",
        )
        self.cat1 = ForumCategory.objects.create(name="Security")
        self.cat2 = ForumCategory.objects.create(name="UI/UX")
        ForumPost.objects.create(
            user=self.user,
            title="Security topic",
            description="Discussion about security",
            category=self.cat1,
            status="open",
        )
        ForumPost.objects.create(
            user=self.user,
            title="UI topic",
            description="Discussion about UI",
            category=self.cat2,
            status="completed",
        )

    def test_forum_page_renders(self):
        url = reverse("view_forum")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Discussion Forum")
        self.assertContains(resp, "Security")
        self.assertContains(resp, "UI/UX")

    def test_forum_filter_endpoint_all(self):
        url = reverse("forum_filter")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("posts", data)
        self.assertEqual(len(data["posts"]), 2)
        self.assertIn("page", data)
        self.assertIn("total_pages", data)
        self.assertIn("total_count", data)

    def test_forum_filter_endpoint_by_category(self):
        url = reverse("forum_filter")
        resp = self.client.get(url, {"category": self.cat1.id})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["posts"]), 1)
        self.assertEqual(data["posts"][0]["category"], "Security")
        self.assertEqual(data["posts"][0]["title"], "Security topic")

    def test_forum_filter_pagination(self):
        url = reverse("forum_filter")
        # create 25 more posts in cat1 to force page 2
        for i in range(25):
            ForumPost.objects.create(
                user=self.user,
                title=f"Extra {i}",
                description="x",
                category=self.cat1,
                status="open",
            )
        resp = self.client.get(url, {"category": self.cat1.id, "page": 2})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["page"], 2)
        self.assertEqual(len(data["posts"]), 6)  # 26 total in cat1 -> 20 on page 1, 6 on page 2

    def test_forum_filter_invalid_page_defaults_to_1(self):
        url = reverse("forum_filter")
        resp = self.client.get(url, {"page": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["page"], 1)

    def test_forum_filter_invalid_category_returns_400(self):
        url = reverse("forum_filter")
        resp = self.client.get(url, {"category": "abc"})
        self.assertEqual(resp.status_code, 400)

    def test_forum_filter_post_method_not_allowed(self):
        url = reverse("forum_filter")
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 405)