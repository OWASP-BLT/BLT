from django.test import TestCase
from django.contrib.auth.models import User
from website.models import UserActivity, Organization

class UserActivityModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.org = Organization.objects.create(name='Test Org', url='https://test.com')
    
    def test_create_user_activity(self):
        """Test creating a UserActivity record"""
        activity = UserActivity.objects.create(
            user=self.user,
            organization=self.org,
            activity_type='bug_report',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            metadata={'issue_id': 123}
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.organization, self.org)
        self.assertEqual(activity.activity_type, 'bug_report')
        self.assertIn('issue_id', activity.metadata)
    
    def test_activity_type_choices(self):
        """Test that activity type choices are valid"""
        valid_types = [choice[0] for choice in UserActivity.ACTIVITY_TYPES]
        self.assertIn('bug_report', valid_types)
        self.assertIn('bug_comment', valid_types)
        self.assertIn('dashboard_visit', valid_types)
    
    def test_str_representation(self):
        """Test string representation"""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login'
        )
        self.assertIn(self.user.username, str(activity))
        self.assertIn('Login', str(activity))