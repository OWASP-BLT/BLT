from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from comments.models import Comment
from website.models import Post, UserProfile


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class BlogCommentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user)
        self.post = Post.objects.create(title="Test Post", content="Test Content", author=self.user)
        self.client.login(username="testuser", password="12345")

    def test_add_comment(self):
        url = reverse("comment_on_content", args=[self.post.pk])
        data = {"content_type": "post", "comment": "This is a test comment."}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Comment.objects.filter(content_type__model="post", object_id=self.post.pk).exists())

    def test_update_comment(self):
        comment = Comment.objects.create(
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.pk,
            author=self.user.username,
            author_fk=self.user_profile,
            text="Original comment",
        )
        url = reverse("update_content_comment", args=[self.post.pk, comment.pk])
        data = {"content_type": "post", "comment": "Updated comment"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.text, "Updated comment")

    def test_delete_comment(self):
        comment = Comment.objects.create(
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.pk,
            author=self.user.username,
            author_fk=self.user_profile,
            text="Comment to be deleted",
        )
        url = reverse("delete_content_comment")
        data = {"content_type": "post", "content_pk": self.post.pk, "comment_pk": comment.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

