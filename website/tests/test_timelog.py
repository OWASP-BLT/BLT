"""
Tests for TimeLog model and API endpoints
"""
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from website.models import Organization, TimeLog


class TimeLogModelTest(TestCase):
    """Test TimeLog model functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organization = Organization.objects.create(
            name='Test Org',
            url='https://testorg.com'
        )

    def test_create_timelog(self):
        """Test creating a basic timelog"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now(),
            github_issue_url='https://github.com/test/repo/issues/1',
            github_issue_number=1,
            github_repo='test/repo'
        )
        self.assertIsNotNone(timelog.id)
        self.assertEqual(timelog.user, self.user)
        self.assertFalse(timelog.is_paused)
        self.assertIsNone(timelog.end_time)

    def test_pause_timelog(self):
        """Test pausing a timelog"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        
        result = timelog.pause()
        self.assertTrue(result)
        self.assertTrue(timelog.is_paused)
        self.assertIsNotNone(timelog.last_pause_time)

    def test_pause_already_paused(self):
        """Test pausing an already paused timelog"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        timelog.pause()
        
        # Try to pause again
        result = timelog.pause()
        self.assertFalse(result)

    def test_resume_timelog(self):
        """Test resuming a paused timelog"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        timelog.pause()
        
        result = timelog.resume()
        self.assertTrue(result)
        self.assertFalse(timelog.is_paused)
        self.assertIsNone(timelog.last_pause_time)
        self.assertIsNotNone(timelog.paused_duration)

    def test_resume_not_paused(self):
        """Test resuming a timelog that isn't paused"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        
        result = timelog.resume()
        self.assertFalse(result)

    def test_duration_calculation(self):
        """Test duration calculation with paused time"""
        start = timezone.now() - timedelta(hours=2)
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=start
        )
        
        # Simulate 30 minutes of paused time
        timelog.paused_duration = timedelta(minutes=30)
        timelog.end_time = timezone.now()
        timelog.save()
        
        # Duration should be ~1.5 hours (2 hours - 30 minutes)
        self.assertIsNotNone(timelog.duration)
        self.assertGreater(timelog.duration.total_seconds(), 5000)  # ~1.4 hours

    def test_get_active_duration(self):
        """Test getting active duration for running timer"""
        start = timezone.now() - timedelta(minutes=30)
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=start
        )
        
        active_duration = timelog.get_active_duration()
        self.assertGreater(active_duration.total_seconds(), 1700)  # ~28+ minutes

    def test_get_active_duration_with_pause(self):
        """Test active duration excludes paused time"""
        start = timezone.now() - timedelta(hours=1)
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=start,
            paused_duration=timedelta(minutes=15)
        )
        
        active_duration = timelog.get_active_duration()
        # Should be ~45 minutes (1 hour - 15 minutes)
        self.assertLess(active_duration.total_seconds(), 3000)


class TimeLogAPITest(APITestCase):
    """Test TimeLog API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_start_timer_api(self):
        """Test starting a timer via API"""
        url = reverse('timelogs-start')
        data = {
            'github_issue_url': 'https://github.com/test/repo/issues/1',
            'github_issue_number': 1,
            'github_repo': 'test/repo'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('start_time', response.data)

    def test_stop_timer_api(self):
        """Test stopping a timer via API"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        
        url = reverse('timelogs-stop', kwargs={'pk': timelog.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['end_time'])
        self.assertIsNotNone(response.data['duration'])

    def test_pause_timer_api(self):
        """Test pausing a timer via API"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        
        url = reverse('timelogs-pause', kwargs={'pk': timelog.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_paused'])

    def test_pause_completed_timer(self):
        """Test pausing a completed timer returns error"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now()
        )
        
        url = reverse('timelogs-pause', kwargs={'pk': timelog.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resume_timer_api(self):
        """Test resuming a timer via API"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        timelog.pause()
        
        url = reverse('timelogs-resume', kwargs={'pk': timelog.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_paused'])

    def test_resume_not_paused_timer(self):
        """Test resuming a timer that isn't paused returns error"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        
        url = reverse('timelogs-resume', kwargs={'pk': timelog.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthorized_pause(self):
        """Test that users can't pause other users' timers"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        timelog = TimeLog.objects.create(
            user=other_user,
            start_time=timezone.now()
        )
        
        url = reverse('timelogs-pause', kwargs={'pk': timelog.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_timelogs(self):
        """Test listing user's timelogs"""
        TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1)
        )
        TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now()
        )
        
        url = reverse('timelogs-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_active_duration_in_response(self):
        """Test that active_duration is included in API response"""
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now() - timedelta(minutes=30)
        )
        
        url = reverse('timelogs-detail', kwargs={'pk': timelog.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('active_duration', response.data)
        self.assertGreater(response.data['active_duration'], 1700)


class GitHubWebhookTest(TestCase):
    """Test GitHub webhook integration"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()

    def test_issue_assigned_webhook(self):
        """Test webhook when issue is assigned"""
        url = reverse('github-timer-webhook')
        payload = {
            'action': 'assigned',
            'issue': {
                'number': 123,
                'html_url': 'https://github.com/test/repo/issues/123'
            },
            'assignee': {
                'login': 'testuser'
            },
            'repository': {
                'full_name': 'test/repo'
            }
        }
        
        response = self.client.post(
            url,
            payload,
            format='json',
            HTTP_X_GITHUB_EVENT='issues'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.json())

    def test_issue_closed_webhook(self):
        """Test webhook when issue is closed"""
        # Create an active timer
        timelog = TimeLog.objects.create(
            user=self.user,
            start_time=timezone.now(),
            github_issue_number=123,
            github_repo='test/repo'
        )
        
        url = reverse('github-timer-webhook')
        payload = {
            'action': 'closed',
            'issue': {
                'number': 123,
                'html_url': 'https://github.com/test/repo/issues/123'
            },
            'repository': {
                'full_name': 'test/repo'
            }
        }
        
        response = self.client.post(
            url,
            payload,
            format='json',
            HTTP_X_GITHUB_EVENT='issues'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify timer was stopped
        timelog.refresh_from_db()
        self.assertIsNotNone(timelog.end_time)

    def test_invalid_json_webhook(self):
        """Test webhook with invalid JSON"""
        url = reverse('github-timer-webhook')
        response = self.client.post(
            url,
            'invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
