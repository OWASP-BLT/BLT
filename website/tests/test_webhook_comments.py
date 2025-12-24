import json
from django.test import TestCase, Client
from django.urls import reverse
from website.models import GitHubIssue, Repo, UserProfile, GitHubComment, User

class GitHubCommentWebhookTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("github-webhook")
        self.repo = Repo.objects.create(repo_url="https://github.com/owner/repo")
        self.user = User.objects.create(username="testuser")
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user, defaults={"github_url": "https://github.com/testuser"})
        if not created:
            self.user_profile.github_url = "https://github.com/testuser"
            self.user_profile.save()
        self.issue = GitHubIssue.objects.create(
            issue_id=1,
            repo=self.repo,
            title="Test PR",
            type="pull_request",
            state="open",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z"
        )

    def test_issue_comment_on_pr(self):
        payload = {
            "action": "created",
            "issue": {
                "number": 1,
                "pull_request": {}, # Indicates it is a PR
            },
            "comment": {
                "id": 1001,
                "body": "This is a comment",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/owner/repo/issues/1#issuecomment-1001"
            },
            "repository": {
                "html_url": "https://github.com/owner/repo",
                "full_name": "owner/repo"
            },
            "sender": {
                "login": "testuser",
                "html_url": "https://github.com/testuser",
                "type": "User"
            }
        }
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issue_comment"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GitHubComment.objects.filter(comment_id=1001).exists())
        comment = GitHubComment.objects.get(comment_id=1001)
        self.assertEqual(comment.github_issue, self.issue)
        self.assertEqual(comment.user_profile, self.user_profile)

    def test_issue_comment_not_on_pr(self):
        payload = {
            "action": "created",
            "issue": {
                "number": 1,
                # No pull_request key
            },
            "comment": {
                "id": 1002,
                "body": "This is a comment on an issue",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/owner/repo/issues/1#issuecomment-1002"
            },
            "repository": {
                "html_url": "https://github.com/owner/repo",
                "full_name": "owner/repo"
            },
            "sender": {
                "login": "testuser",
                "type": "User"
            }
        }
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issue_comment"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(GitHubComment.objects.filter(comment_id=1002).exists())

    def test_bot_comment_ignored(self):
        payload = {
            "action": "created",
            "issue": {
                "number": 1,
                "pull_request": {},
            },
            "comment": {
                "id": 1003,
                "body": "I am a bot",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "html_url": "https://github.com/owner/repo/issues/1#issuecomment-1003"
            },
            "repository": {
                "html_url": "https://github.com/owner/repo",
                "full_name": "owner/repo"
            },
            "sender": {
                "login": "copilot",
                "type": "Bot"
            }
        }
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issue_comment"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(GitHubComment.objects.filter(comment_id=1003).exists())
