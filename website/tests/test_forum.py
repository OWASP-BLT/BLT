from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from website.models import ForumCategory, ForumPost


class ForumViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass12345")
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

    def test_forum_filter_endpoint_by_category(self):
        url = reverse("forum_filter")
        resp = self.client.get(url, {"category": self.cat1.id})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["posts"]), 1)
        self.assertEqual(data["posts"][0]["category"], "Security")
        self.assertEqual(data["posts"][0]["title"], "Security topic")
