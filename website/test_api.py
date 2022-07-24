from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from PIL import Image

class APITests(APITestCase):

    register_url = '/auth/registration/'
    login_url = '/auth/login/'

    USERNAME = 'person'
    PASS = 'Gassword123&&'
    EMAIL = 'person1@world.com'

    REGISTRATION_DATA = {
        'username': USERNAME,
        'password1': PASS,
        'password2': PASS,
        'email': EMAIL,
    }

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
        url = "/api/v1/issues/"

        _file = open("website/static/img/background.png", 'rb')

        data = {
            'url': 'http://www.bugheist.com',
            'description': 'test',
            'screenshot': _file,
            'label': '0',
            'token': 'test',
            'type': 'test',
            }
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
