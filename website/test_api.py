from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from PIL import Image
from django.core import mail
from django.utils.encoding import force_str
from django.db.transaction import atomic

class APITests(APITestCase):

    register_url = '/auth/registration/'
    login_url = '/auth/login/'
    password_reset_url = '/auth/password/reset/'

    USERNAME = 'person'
    PASS = 'Gassword123&&'
    NEW_PASS = 'Gasswoasdfas2234'
    EMAIL = 'person1@world.com'

    REGISTRATION_DATA = {
        'username': USERNAME,
        'password1': PASS,
        'password2': PASS,
        'email': EMAIL,
    }

    def _generate_uid_and_token(self, user):
        result = {}

        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        result['uid'] = urlsafe_base64_encode(force_bytes(user.pk))
        result['token'] = default_token_generator.make_token(user)
        return result

    def test_login_by_email(self):
        payload = {
            'username': self.USERNAME.lower(),
            'password': self.PASS,
        }

        user = get_user_model().objects.create_user(self.USERNAME, self.EMAIL, self.PASS)

        response = self.client.post(self.login_url, data=payload, status_code=200)
        self.assertEqual('key' in response.json().keys(), True)
        self.token = response.json()['key']

        payload = {
            'username': self.USERNAME.lower(),
            'password': self.PASS,
        }
        response = self.client.post(self.login_url, data=payload)
        self.assertEqual('key' in response.json().keys(), True)
        self.token = response.json()['key']


    def test_registration(self):
        user_count = get_user_model().objects.all().count()
        result = self.client.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertIn('key', result.data)
        self.assertEqual(get_user_model().objects.all().count(), user_count + 1)

        new_user = get_user_model().objects.latest('id')
        self.assertEqual(new_user.username, self.REGISTRATION_DATA['username'])

    def test_create_issue(self):

        @atomic 
        def create_issue():
            url = "/api/v1/issues/"
            with open("website/static/img/background.png", 'rb') as _file:
                data = {
                    'url': 'http://www.google.com',
                    'description': 'test',
                    'screenshot': _file,
                    'label': '0',
                    'token': 'test',
                    'type': 'test',
                    }
                response = self.client.post(url, data, format='multipart')
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        return create_issue

    def test_password_reset(self):
        user = get_user_model().objects.create_user(self.USERNAME, self.EMAIL, self.PASS)

        mail_count = len(mail.outbox)
        payload = {'email': self.EMAIL}
        self.client.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count + 1)

        url_kwargs = self._generate_uid_and_token(user)
        url = reverse('rest_password_reset_confirm')


        data = {
            'new_password1': self.NEW_PASS,
            'new_password2': self.NEW_PASS,
            'uid': force_str(url_kwargs['uid']),
            'token': url_kwargs['token'],
        }
        url = reverse('rest_password_reset_confirm')
        self.client.post(url, data=data, status_code=200)
        for item in mail.outbox:
            print(item.__dict__)

