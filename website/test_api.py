from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
#from myproject.apps.core.models import Account
from PIL import Image

class APITests(APITestCase):
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
