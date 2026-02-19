from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.conf import settings

class DualLoginTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user with a specific username and email
        self.username = "testuser"
        self.email = "testuser@example.com"
        self.password = "testpassword123"
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password
        )
        # Ensure email is verified in allauth terms if needed
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(
            user=self.user,
            email=self.email,
            verified=True,
            primary=True
        )

    def test_login_with_username(self):
        """Verify that login works with username"""
        login_url = reverse("account_login")
        response = self.client.post(login_url, {
            "login": self.username,
            "password": self.password
        }, follow=True)
        
        # Check if login was successful
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertEqual(response.context["user"].username, self.username)

    def test_login_with_email(self):
        """Verify that login now works with email thanks to updated setting"""
        login_url = reverse("account_login")
        response = self.client.post(login_url, {
            "login": self.email,
            "password": self.password
        }, follow=True)
        
        # Check if login was successful
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertEqual(response.context["user"].email, self.email)

    def test_incorrect_credentials_error_displayed(self):
        """Verify that incorrect credentials show an error message (fixing suppression)"""
        login_url = reverse("account_login")
        response = self.client.post(login_url, {
            "login": self.username,
            "password": "wrongpassword"
        })
        
        # Should stay on the same page
        self.assertEqual(response.status_code, 200)
        
        # Verify non_field_errors contains the expected error message
        form = response.context["form"]
        self.assertTrue(form.non_field_errors())
        
        # Check if the error message is present in the HTML content
        # (This confirms the template now renders non_field_errors)
        self.assertContains(response, "The username and/or password you specified are not correct.")
