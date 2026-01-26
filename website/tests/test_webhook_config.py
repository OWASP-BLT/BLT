from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock

from website.models import (
    Project, Repo, GitHubWebhookConfig,
    Organization, Contributor, ContributorStats
)
from website.tasks import recalculate_repo_stats

User = get_user_model()


class GitHubWebhookConfigModelTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.project = Project.objects.create(
            name="Test Project",
            organization=self.org
        )
    
    def test_create_webhook_config(self):
        """Test creating a webhook configuration."""
        config = GitHubWebhookConfig.objects.create(
            project=self.project,
            stats_recalc_enabled=True
        )
        
        self.assertTrue(config.stats_recalc_enabled)
        self.assertIsNone(config.webhook_secret)
        self.assertIsNone(config.last_webhook_received)
        self.assertEqual(str(config), f"Webhook Config for {self.project.name}")
    
    def test_one_config_per_project(self):
        """Test that only one config can exist per project."""
        GitHubWebhookConfig.objects.create(
            project=self.project,
            stats_recalc_enabled=True
        )
        
        # Attempting to create another should raise an exception
        with self.assertRaises(Exception):
            GitHubWebhookConfig.objects.create(
                project=self.project,
                stats_recalc_enabled=False
            )


class WebhookConfigAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Use get_or_create to avoid IntegrityError
        self.token, created = Token.objects.get_or_create(user=self.user)
        
        self.org = Organization.objects.create(
            name="Test Org",
            url="https://testorg.com"  # Required field
        )
        # FIXED: Set user as admin (ForeignKey, not ManyToMany)
        self.org.admin = self.user
        self.org.save()
        
        self.project = Project.objects.create(
            name="Test Project",
            organization=self.org
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
    
    def test_get_config_not_exists(self):
        """Test GET when config doesn't exist returns defaults."""
        url = f'/api/projects/{self.project.id}/webhook-config/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['stats_recalc_enabled'])
        self.assertFalse(response.data['has_custom_secret'])
    
    def test_enable_stats_recalc(self):
        """Test enabling stats recalculation via PUT."""
        url = f'/api/projects/{self.project.id}/webhook-config/'
        data = {'stats_recalc_enabled': True}
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['stats_recalc_enabled'])
        
        # Verify in database
        config = GitHubWebhookConfig.objects.get(project=self.project)
        self.assertTrue(config.stats_recalc_enabled)


class StatsRecalculationTaskTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Test Org",
            url="https://testorg.com"
        )
        self.project = Project.objects.create(
            name="Test Project",
            organization=self.org
        )
        self.repo = Repo.objects.create(
            name="test-repo",
            repo_url="https://github.com/test-owner/test-repo",
            project=self.project
        )
    
    @patch('website.tasks.requests.get')
    def test_recalculate_repo_stats(self, mock_get):
        """Test the recalculate_repo_stats task."""
        # Mock GitHub API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        # Call the task
        result = recalculate_repo_stats(self.repo.id)
        
        # Verify result
        self.assertEqual(result['status'], 'success')
        
        # Verify API was called
        mock_get.assert_called_once()