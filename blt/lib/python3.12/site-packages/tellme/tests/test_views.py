import json
import base64

import faker
from factory.django import ImageField

from django.test import TestCase
try:
    from django.core.urlresolvers import reverse_lazy as reverse
except ImportError:
    from django.urls import reverse_lazy as reverse
from django.core import mail

from tellme.tests import factories
from tellme.models import Feedback

fake = faker.Faker()


def make_base64_img():
    params = {'format': 'PNG'}
    img = ImageField()._make_data(params)
    base64_img = base64.b64encode(img).decode()
    return 'image/png;base64,%s' % base64_img


class PostFeedbackViewTest(TestCase):
    url = reverse('tellme:post_feedback')

    def test_non_ajax(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

    def test_non_post(self):
        for method in ('get', 'patch', 'put', 'delete'):
            response = self.client.generic(method, self.url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 400)

    def test_authenticated_user(self):
        user = factories.UserFactory()
        self.client.force_login(user)
        data = {
            'feedback': json.dumps({
                'url': fake.url(),
                'browser': fake.user_agent(),
                'note': fake.sentence(),
                'img': make_base64_img(),
            })
        }
        response = self.client.post(self.url, data=data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        feedback = Feedback.objects.last()
        self.assertIsNotNone(feedback, response.content)
        self.assertEqual(feedback.user, user)
        self.assertEqual(len(mail.outbox), 1)

    def test_with_email_user(self):
        email = fake.email()
        data = {
            'feedback': json.dumps({
                'url': fake.url(),
                'browser': fake.user_agent(),
                'note': fake.sentence(),
                'img': make_base64_img(),
                'email': email,
            })
        }
        response = self.client.post(self.url, data=data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        feedback = Feedback.objects.last()
        self.assertIsNotNone(feedback, response.content)
        self.assertIsNone(feedback.user)
        self.assertEqual(feedback.email, email)
        self.assertEqual(len(mail.outbox), 1)

    def test_with_invalid_form(self):
        email = fake.email()
        data = {
            'feedback': json.dumps({
                'url': fake.url(),
                'browser': fake.user_agent(),
                'note': fake.sentence(),
                'img': make_base64_img(),
                'email': 'foo',
            })
        }
        response = self.client.post(self.url, data=data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        errors = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', errors)
        exists = Feedback.objects.exists()
        self.assertFalse(exists)
        self.assertEqual(len(mail.outbox), 0)


class GetFeedbackScreenshotViewTest(TestCase):
    def test_screenshot_view(self):
        feedback = Feedback.objects.create(
            url=fake.url(),
            browser=fake.user_agent(),
            comment=fake.sentence(),
            screenshot=make_base64_img(),
            email=fake.email(),
        )
        response = self.client.get(feedback.get_screenshot_url())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], feedback.screenshot.url)