import shutil
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from website.models import Post


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostDetailViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username="author",
            password="testpass123",
            email="author@example.com",
        )

        # Minimal valid 1x1 PNG image
        self.image = SimpleUploadedFile(
            "test.png",
            (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
                b"\x00\x00\x00\nIDATx\xdac\xf8\xff\xff?\x00\x05\xfe\x02\xfeA"
                b"\xe2\x1c\x00\x00\x00\x00IEND\xaeB`\x82"
            ),
            content_type="image/png",
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