from django.test import TestCase
try:
    from django.core.urlresolvers import reverse_lazy as reverse
except ImportError:
    from django.urls import reverse_lazy as reverse

from tellme.models import Feedback
from tellme.tests import factories


class AdminAcknowledgeActionTest(TestCase):
    url = reverse('admin:tellme_feedback_changelist')

    def test_action(self):
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        feedback = factories.FeedbackFactory(ack=False)
        self.client.force_login(user)
        data = {
            'action': 'acknowledge',
            '_selected_action': [feedback.id],
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        feedback.refresh_from_db()
        self.assertTrue(feedback.ack)


class AdminUnacknowledgeActionTest(TestCase):
    url = reverse('admin:tellme_feedback_changelist')

    def test_action(self):
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        feedback = factories.FeedbackFactory(ack=True)
        self.client.force_login(user)
        data = {
            'action': 'unacknowledge',
            '_selected_action': [feedback.id],
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        feedback.refresh_from_db()
        self.assertFalse(feedback.ack)
