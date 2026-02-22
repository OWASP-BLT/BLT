from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from website.models import Post


class PostDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="author",
            password="testpass123",
            email="author@example.com",
        )

        # Create dummy image
        self.image = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg",
        )

        self.post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            author=self.user,
            content="**Bold Text**",
            image=self.image,
        )

    def test_post_detail_view_loads(self):
        response = self.client.get(
            reverse("post_detail", kwargs={"slug": self.post.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Post")

    def test_markdown_is_rendered(self):
        response = self.client.get(
            reverse("post_detail", kwargs={"slug": self.post.slug})
        )
        self.assertContains(response, "<strong>Bold Text</strong>", html=True)