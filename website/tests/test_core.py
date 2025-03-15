import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import ForumCategory, ForumPost


class ForumTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.category = ForumCategory.objects.create(name="Test Category", description="Test Description")
        self.client.login(username="testuser", password="testpass")

        self.post_data = {"title": "Test Post", "category": self.category.id, "description": "Test Description"}

    def test_create_and_view_forum_post(self):
        # Create a new forum post
        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(self.post_data), content_type="application/json"
        )

        # Check if post was created successfully
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify post exists in database
        post = ForumPost.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.title, self.post_data["title"])
        self.assertEqual(post.description, self.post_data["description"])
        self.assertEqual(post.category_id, self.post_data["category"])
        self.assertEqual(post.user, self.user)

        # View the forum page
        response = self.client.get(reverse("view_forum"))

        # Check if page loads successfully
        self.assertEqual(response.status_code, 200)

        # Check if our post is in the context
        self.assertIn("posts", response.context)
        self.assertIn(post, response.context["posts"])

        # Check if post content is in the response
        self.assertContains(response, self.post_data["title"])
        self.assertContains(response, self.post_data["description"])

    def test_forum_post_voting(self):
        # Create a test post first
        post = ForumPost.objects.create(
            user=self.user, title="Test Post for Voting", description="Test Description", category=self.category
        )

        # Test upvoting
        response = self.client.post(
            reverse("vote_forum_post"),
            data=json.dumps({"post_id": post.id, "up_vote": True, "down_vote": False}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["up_vote"], 1)
        self.assertEqual(data["down_vote"], 0)

        # Test downvoting
        response = self.client.post(
            reverse("vote_forum_post"),
            data=json.dumps({"post_id": post.id, "up_vote": False, "down_vote": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["up_vote"], 0)
        self.assertEqual(data["down_vote"], 1)

        # Verify vote counts in database
        post.refresh_from_db()
        self.assertEqual(post.up_votes, 0)
        self.assertEqual(post.down_votes, 1)

    def test_forum_post_commenting(self):
        # Create a test post first
        post = ForumPost.objects.create(
            user=self.user, title="Test Post for Comments", description="Test Description", category=self.category
        )

        # Test adding a comment
        comment_data = {"post_id": post.id, "content": "Test comment content"}

        response = self.client.post(
            reverse("add_forum_comment"), data=json.dumps(comment_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify comment exists in database
        self.assertEqual(post.comments.count(), 1)
        comment = post.comments.first()
        self.assertEqual(comment.content, comment_data["content"])
        self.assertEqual(comment.user, self.user)

        # View the forum page and check if comment is displayed
        response = self.client.get(reverse("view_forum"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, comment_data["content"])

