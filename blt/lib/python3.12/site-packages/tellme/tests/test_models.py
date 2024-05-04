from unittest import mock
from django.test import TestCase
from tellme.models import Feedback
from tellme.tests.factories import FeedbackFactory

try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse


class FeedbackScreenshotMethodsTest(TestCase):
    @mock.patch('tellme.models.reverse', wraps=reverse)
    def test_get_screenshot_url(self, mocked_reverse):
        feedback = FeedbackFactory()
        url = feedback.get_screenshot_url()
        self.assertEqual(url, '/tellme/get_feedback_screenshot/%s/' % feedback.pk)
        mocked_reverse.assert_called_once_with('tellme:get_feedback_screenshot', kwargs={'pk': feedback.pk})


class FeedbackScreenshotDeleteTest(TestCase):
    def test_delete_screenshot(self):
        feedback = FeedbackFactory()
        self.assertTrue(feedback.screenshot)
        feedback.delete()
        self.assertFalse(feedback.screenshot)

    def test_no_screenshot(self):
        feedback = FeedbackFactory(screenshot=None)
        feedback.delete()
        self.assertFalse(feedback.screenshot)