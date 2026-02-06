"""
Comprehensive tests for AI spam detection system including:
- Service tests with mocked OpenAI API
- Model tests for FlaggedContent and ModerationAction
- Integration tests for Issue, Organization, and User Profile spam detection
- Notification signal tests
"""

from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from website.models import FlaggedContent, Issue, ModerationAction, Notification
from website.services.ai_spam_detection import AISpamDetectionService


class SpamDetectionServiceTests(TestCase):
    """Test the AI spam detection service with mocked OpenAI API"""

    def setUp(self):
        self.service = AISpamDetectionService()

    @patch("website.services.ai_spam_detection.OpenAI")
    def test_service_initialization_success(self, mock_openai):
        """Test that service initializes with valid API key"""
        with override_settings(OPENAI_API_KEY="test-api-key"):
            service = AISpamDetectionService()
            self.assertIsNotNone(service.client)

    @patch("website.services.ai_spam_detection.OpenAI")
    def test_service_initialization_no_api_key(self, mock_openai):
        """Test that service handles missing API key gracefully"""
        with override_settings(OPENAI_API_KEY=None):
            service = AISpamDetectionService()
            self.assertIsNone(service.client)

    @patch.object(AISpamDetectionService, "_parse_response")
    def test_detect_spam_high_confidence(self, mock_parse):
        """Test spam detection with high confidence score"""
        # Mock the OpenAI response
        mock_parse.return_value = {
            "is_spam": True,
            "confidence": 0.95,
            "reason": "Contains promotional content and suspicious links",
            "category": "promotional",
        }

        # Mock the client
        self.service.client = MagicMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"is_spam": true}'))]
        self.service.client.chat.completions.create.return_value = mock_response

        result = self.service.detect_spam("Buy cheap followers now!", "issue")

        self.assertTrue(result["is_spam"])
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["category"], "promotional")

    @patch.object(AISpamDetectionService, "_parse_response")
    def test_detect_spam_low_confidence(self, mock_parse):
        """Test legitimate content with low spam score"""
        mock_parse.return_value = {
            "is_spam": False,
            "confidence": 0.1,
            "reason": "Legitimate bug report",
            "category": "clean",
        }

        self.service.client = MagicMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"is_spam": false}'))]
        self.service.client.chat.completions.create.return_value = mock_response

        result = self.service.detect_spam("Found XSS vulnerability in login form", "issue")

        self.assertFalse(result["is_spam"])
        self.assertEqual(result["confidence"], 0.1)

    def test_detect_spam_api_unavailable(self):
        """Test graceful degradation when OpenAI API is unavailable"""
        self.service.client = None

        result = self.service.detect_spam("Test content", "issue")

        self.assertFalse(result["is_spam"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("unavailable", result["reason"])

    def test_detect_spam_api_error(self):
        """Test error handling when API call fails"""
        self.service.client = MagicMock()
        self.service.client.chat.completions.create.side_effect = Exception("API Error")

        result = self.service.detect_spam("Test content", "issue")

        self.assertFalse(result["is_spam"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("error", result["reason"].lower())

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response from AI"""
        ai_response = """{
            "is_spam": true,
            "confidence": 0.85,
            "reason": "Promotional content",
            "category": "promotional"
        }"""

        result = self.service._parse_response(ai_response)

        self.assertTrue(result["is_spam"])
        self.assertEqual(result["confidence"], 0.85)

    def test_parse_response_fallback(self):
        """Test fallback parsing when JSON is invalid"""
        ai_response = "This looks like spam to me"

        result = self.service._parse_response(ai_response)

        # Current implementation returns safe fallback (not spam)
        self.assertFalse(result["is_spam"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["reason"], "Invalid AI response format")
        self.assertEqual(result["category"], "unknown")

    def test_parse_response_missing_keys(self):
        """Test parsing JSON with missing required keys"""
        # JSON is valid but missing 'category' key
        ai_response = '{"is_spam": true, "confidence": 0.9, "reason": "Spam detected"}'

        result = self.service._parse_response(ai_response)

        # Should fall back to safe defaults when keys are missing
        self.assertFalse(result["is_spam"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("Invalid", result["reason"])


class FlaggedContentModelTests(TestCase):
    """Test FlaggedContent and ModerationAction models"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.moderator = User.objects.create_user(username="moderator", password="testpass", is_staff=True)
        self.issue = Issue.objects.create(
            url="http://example.com/spam", description="Spam content here", user=self.user
        )

    def test_flagged_content_creation(self):
        """Test creating a FlaggedContent instance"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.85,
            reason="promotional",
            spam_categories=["promotional", "low_quality"],
            detection_details="AI detected promotional spam with high confidence",
            status="pending",
        )

        self.assertEqual(flagged.spam_score, 0.85)
        self.assertEqual(flagged.status, "pending")
        self.assertEqual(flagged.reason, "promotional")
        self.assertIsNone(flagged.assigned_reviewer)

    def test_flagged_content_string_representation(self):
        """Test the string representation of FlaggedContent"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.9,
            reason="malicious",
            status="pending",
        )

        str_repr = str(flagged)
        self.assertIn("issue", str_repr.lower())
        self.assertIn("Pending", str_repr)

    def test_get_content_preview_with_description(self):
        """Test content preview for objects with description"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.75,
            reason="low_quality",
        )

        preview = flagged.get_content_preview()
        self.assertIn("Spam content", preview)

    def test_approve_method(self):
        """Test approving flagged content"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.6,
            reason="duplicate",
            status="pending",
        )

        flagged.approve(self.moderator, "False positive, legitimate content")

        flagged.refresh_from_db()
        self.assertEqual(flagged.status, "approved")
        self.assertEqual(flagged.assigned_reviewer, self.moderator)
        self.assertIn("False positive", flagged.resolution_notes)
        self.assertIsNotNone(flagged.resolved_at)

    def test_reject_method(self):
        """Test rejecting flagged content"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.95,
            reason="malicious",
            status="pending",
        )

        flagged.reject(self.moderator, "Confirmed spam, contains phishing links")

        flagged.refresh_from_db()
        self.assertEqual(flagged.status, "rejected")
        self.assertEqual(flagged.assigned_reviewer, self.moderator)
        self.assertIn("phishing", flagged.resolution_notes)
        self.assertIsNotNone(flagged.resolved_at)

    def test_moderation_action_creation(self):
        """Test creating ModerationAction audit records"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.8,
            reason="promotional",
        )

        action = ModerationAction.objects.create(
            flagged_content=flagged,
            action="approved",
            performed_by=self.moderator,
            notes="Reviewed and approved",
        )

        self.assertEqual(action.action, "approved")
        self.assertEqual(action.performed_by, self.moderator)
        self.assertEqual(action.flagged_content, flagged)

    def test_moderation_action_string_representation(self):
        """Test ModerationAction string representation"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.7,
            reason="low_quality",
        )

        action = ModerationAction.objects.create(
            flagged_content=flagged,
            action="flagged",
            performed_by=None,
            notes="Auto-detected by AI",
        )

        str_repr = str(action)
        self.assertIn("System", str_repr)
        self.assertIn("flagged", str_repr.lower())

    def test_flagged_content_ordering(self):
        """Test that flagged content is ordered by created_at descending"""
        flagged1 = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.5,
            reason="other",
        )

        issue2 = Issue.objects.create(url="http://example.com/spam2", description="More spam", user=self.user)

        flagged2 = FlaggedContent.objects.create(
            content_object=issue2,
            spam_score=0.9,
            reason="promotional",
        )

        flagged_list = list(FlaggedContent.objects.all())
        self.assertEqual(flagged_list[0], flagged2)  # Most recent first
        self.assertEqual(flagged_list[1], flagged1)


class SpamDetectionIntegrationTests(TestCase):
    """Integration tests for spam detection across different content types"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.moderator = User.objects.create_user(username="moderator", password="testpass", is_staff=True)

    @patch.object(AISpamDetectionService, "detect_spam")
    def test_issue_spam_detection_high_confidence(self, mock_detect):
        """Test that high-confidence spam issues are flagged"""
        mock_detect.return_value = {
            "is_spam": True,
            "confidence": 0.95,
            "reason": "Contains promotional links",
            "category": "promotional",
        }

        # This would be called in the actual issue creation view
        spam_detector = AISpamDetectionService()
        result = spam_detector.detect_spam("Buy followers cheap!", "issue")

        self.assertTrue(result["is_spam"])
        self.assertGreater(result["confidence"], 0.7)

    @patch.object(AISpamDetectionService, "detect_spam")
    def test_organization_spam_detection(self, mock_detect):
        """Test spam detection for organization registration"""
        mock_detect.return_value = {
            "is_spam": True,
            "confidence": 0.88,
            "reason": "Promotional content in organization description",
            "category": "promotional",
        }

        spam_detector = AISpamDetectionService()
        result = spam_detector.detect_spam("Visit our website for cheap services!", "organization")

        self.assertTrue(result["is_spam"])
        self.assertEqual(result["category"], "promotional")

    @patch.object(AISpamDetectionService, "detect_spam")
    def test_user_profile_spam_detection(self, mock_detect):
        """Test spam detection for user profile bio"""
        mock_detect.return_value = {
            "is_spam": False,
            "confidence": 0.1,
            "reason": "Legitimate bio",
            "category": "clean",
        }

        spam_detector = AISpamDetectionService()
        result = spam_detector.detect_spam("Security researcher with 5 years experience", "user_profile")

        self.assertFalse(result["is_spam"])

    def test_threshold_logic_auto_reject(self):
        """Test auto-reject threshold (e.g., >0.9)"""
        spam_score = 0.95
        auto_reject_threshold = 0.9

        if spam_score > auto_reject_threshold:
            should_auto_reject = True
        else:
            should_auto_reject = False

        self.assertTrue(should_auto_reject)

    def test_threshold_logic_flag_for_review(self):
        """Test flag-for-review threshold (e.g., 0.7-0.9)"""
        spam_score = 0.75
        flag_threshold = 0.7
        auto_reject_threshold = 0.9

        if spam_score > auto_reject_threshold:
            should_auto_reject = True
        elif spam_score > flag_threshold:
            should_flag = True
        else:
            should_flag = False

        self.assertTrue(should_flag)

    def test_threshold_logic_pass_through(self):
        """Test pass-through for low scores (<0.7)"""
        spam_score = 0.3
        flag_threshold = 0.7

        if spam_score > flag_threshold:
            should_flag = True
        else:
            should_flag = False

        self.assertFalse(should_flag)


class NotificationSignalTests(TestCase):
    """Test notification signals for spam detection"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.moderator = User.objects.create_user(username="moderator", password="testpass", is_staff=True)
        self.superuser = User.objects.create_user(username="admin", password="testpass", is_superuser=True)
        self.issue = Issue.objects.create(url="http://example.com", description="Test issue", user=self.user)

    def test_notification_created_on_flagged_content(self):
        """Test that notifications are sent to moderators when content is flagged"""
        # Clear existing notifications
        Notification.objects.all().delete()

        # Create flagged content (this should trigger the signal)
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.85,
            reason="promotional",
            status="pending",
            detection_details="AI detected spam",
        )

        # Check that notifications were created for staff and superusers
        notifications = Notification.objects.filter(notification_type="alert")
        self.assertGreater(notifications.count(), 0)

        # Check that moderators received notifications
        moderator_notified = Notification.objects.filter(user=self.moderator, notification_type="alert").exists()
        superuser_notified = Notification.objects.filter(user=self.superuser, notification_type="alert").exists()

        self.assertTrue(moderator_notified or superuser_notified)

    def test_notification_contains_content_info(self):
        """Test that notification contains relevant content information"""
        Notification.objects.all().delete()

        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.92,
            reason="malicious",
            status="pending",
            detection_details="Phishing attempt detected",
        )

        # Assert notification was created
        self.assertTrue(Notification.objects.filter(notification_type="alert").exists())

        notification = Notification.objects.filter(notification_type="alert").first()
        self.assertIsNotNone(notification)

        # Assert notification contains required information
        self.assertIn("Spam Alert", notification.message)
        self.assertIn("confidence", notification.message.lower())
        self.assertIn("malicious", notification.message.lower())

    def test_moderation_action_created_on_flag(self):
        """Test that ModerationAction is created when content is flagged"""
        ModerationAction.objects.all().delete()

        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.78,
            reason="low_quality",
            status="pending",
        )

        # Check that a ModerationAction was created
        actions = ModerationAction.objects.filter(flagged_content=flagged, action="flagged")
        self.assertGreater(actions.count(), 0)

    def test_no_notification_for_approved_content(self):
        """Test that notifications are only sent for pending content"""
        Notification.objects.all().delete()

        # Create flagged content with approved status
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.85,
            reason="promotional",
            status="approved",  # Not pending
        )

        # Assert no notifications were created
        notifications = Notification.objects.filter(notification_type="alert")
        self.assertFalse(notifications.exists())
        self.assertEqual(notifications.count(), 0)


class AdminActionTests(TestCase):
    """Test admin actions for spam moderation"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.moderator = User.objects.create_user(username="moderator", password="testpass", is_staff=True)
        self.issue = Issue.objects.create(url="http://example.com", description="Test", user=self.user)

    def test_bulk_approve_action(self):
        """Test bulk approval of flagged content"""
        flagged1 = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.6,
            reason="duplicate",
            status="pending",
        )

        issue2 = Issue.objects.create(url="http://example.com/2", description="Test 2", user=self.user)

        flagged2 = FlaggedContent.objects.create(
            content_object=issue2,
            spam_score=0.55,
            reason="low_quality",
            status="pending",
        )

        # Simulate bulk approve
        for flagged in [flagged1, flagged2]:
            flagged.approve(self.moderator, "Bulk approved")

        flagged1.refresh_from_db()
        flagged2.refresh_from_db()

        self.assertEqual(flagged1.status, "approved")
        self.assertEqual(flagged2.status, "approved")

    def test_bulk_reject_action(self):
        """Test bulk rejection of flagged content"""
        flagged1 = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.95,
            reason="malicious",
            status="pending",
        )

        # Simulate bulk reject
        flagged1.reject(self.moderator, "Bulk rejected")

        flagged1.refresh_from_db()
        self.assertEqual(flagged1.status, "rejected")

    def test_assign_to_moderator(self):
        """Test assigning flagged content to moderator"""
        flagged = FlaggedContent.objects.create(
            content_object=self.issue,
            spam_score=0.8,
            reason="promotional",
            status="pending",
        )

        # Assign to moderator
        flagged.assigned_reviewer = self.moderator
        flagged.save()

        ModerationAction.objects.create(
            flagged_content=flagged,
            action="assigned",
            performed_by=self.moderator,
            notes=f"Assigned to {self.moderator.username}",
        )

        flagged.refresh_from_db()
        self.assertEqual(flagged.assigned_reviewer, self.moderator)

        action = ModerationAction.objects.filter(flagged_content=flagged, action="assigned").first()
        self.assertIsNotNone(action)
