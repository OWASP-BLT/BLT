"""
Security-focused tests for organization views, especially open redirect vulnerabilities
and URL validation in forms.
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.forms import OrganizationProfileForm
from website.models import Organization


class OrganizationProfileFormSecurityTests(TestCase):
    """Test URL validation in OrganizationProfileForm to prevent open redirect attacks"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")
        self.organization = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            url="https://test-org.com",
            admin=self.user,
        )

    def test_valid_twitter_url_accepted(self):
        """Test that valid Twitter URLs are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "https://twitter.com/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_valid_x_domain_twitter_url_accepted(self):
        """Test that x.com domain is accepted for Twitter"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "https://x.com/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_twitter_subdomain_accepted(self):
        """Test that Twitter subdomains are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "https://mobile.twitter.com/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_invalid_twitter_domain_rejected(self):
        """Test that non-Twitter domains are rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "https://evil.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("twitter", form.errors)
        self.assertIn("twitter.com or x.com", str(form.errors["twitter"]))

    def test_twitter_domain_suffix_attack_rejected(self):
        """Test that evil.twitter.com.attacker.com is rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "https://twitter.com.evil-attacker.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("twitter", form.errors)

    def test_valid_facebook_url_accepted(self):
        """Test that valid Facebook URLs are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "facebook": "https://facebook.com/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_valid_fb_com_domain_accepted(self):
        """Test that fb.com short domain is accepted for Facebook"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "facebook": "https://fb.com/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_facebook_subdomain_accepted(self):
        """Test that Facebook subdomains are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "facebook": "https://www.facebook.com/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_invalid_facebook_domain_rejected(self):
        """Test that non-Facebook domains are rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "facebook": "https://evil.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("facebook", form.errors)
        self.assertIn("facebook.com or fb.com", str(form.errors["facebook"]))

    def test_facebook_domain_suffix_attack_rejected(self):
        """Test that facebook.com.attacker.com is rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "facebook": "https://facebook.com.evil.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("facebook", form.errors)

    def test_valid_linkedin_url_accepted(self):
        """Test that valid LinkedIn URLs are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "linkedin": "https://linkedin.com/company/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_linkedin_subdomain_accepted(self):
        """Test that LinkedIn subdomains are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "linkedin": "https://www.linkedin.com/company/testorg",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_invalid_linkedin_domain_rejected(self):
        """Test that non-LinkedIn domains are rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "linkedin": "https://evil.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("linkedin", form.errors)
        self.assertIn("linkedin.com", str(form.errors["linkedin"]))

    def test_linkedin_domain_suffix_attack_rejected(self):
        """Test that linkedin.com.attacker.com is rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "linkedin": "https://linkedin.com.malicious.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("linkedin", form.errors)

    def test_valid_discord_url_accepted(self):
        """Test that valid Discord URLs are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "discord_url": "https://discord.gg/abc123",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_discord_com_domain_accepted(self):
        """Test that discord.com domain is accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "discord_url": "https://discord.com/invite/abc123",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_discord_subdomain_accepted(self):
        """Test that Discord subdomains are accepted"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "discord_url": "https://app.discord.com/invite/abc123",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_invalid_discord_domain_rejected(self):
        """Test that non-Discord domains are rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "discord_url": "https://evil.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("discord_url", form.errors)
        self.assertIn("discord.gg or discord.com", str(form.errors["discord_url"]))

    def test_discord_domain_suffix_attack_rejected(self):
        """Test that discord.gg.attacker.com is rejected"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "discord_url": "https://discord.gg.evil.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("discord_url", form.errors)

    def test_empty_social_urls_accepted(self):
        """Test that empty social media URLs are acceptable"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "",
            "facebook": "",
            "linkedin": "",
            "discord_url": "",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_none_social_urls_accepted(self):
        """Test that None social media URLs are acceptable"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_multiple_invalid_urls_show_all_errors(self):
        """Test that multiple invalid URLs show all errors"""
        form_data = {
            "name": "Test Org",
            "url": "https://test-org.com",
            "twitter": "https://evil1.com/phishing",
            "facebook": "https://evil2.com/phishing",
            "linkedin": "https://evil3.com/phishing",
        }
        form = OrganizationProfileForm(data=form_data, instance=self.organization)
        self.assertFalse(form.is_valid())
        self.assertIn("twitter", form.errors)
        self.assertIn("facebook", form.errors)
        self.assertIn("linkedin", form.errors)


class OrganizationSocialRedirectSecurityTests(TestCase):
    """Test OrganizationSocialRedirectView security against open redirect attacks"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

    def test_redirect_blocks_evil_twitter_domain(self):
        """Test that redirects block non-Twitter domains"""
        org = Organization.objects.create(
            name="Evil Twitter Org",
            slug="evil-twitter",
            url="https://evil-twitter.com",
            twitter="https://evil-site.com/steal-credentials",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        # Should not redirect to evil-site.com
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil-site.com", response.url)
        self.assertIn(f"/organization/{org.id}/dashboard/analytics/", response.url)

    def test_redirect_blocks_domain_suffix_attack(self):
        """Test that twitter.com.attacker.com is blocked"""
        org = Organization.objects.create(
            name="Suffix Attack Org",
            slug="suffix-attack",
            url="https://suffix-attack.com",
            twitter="https://twitter.com.evil-attacker.com/phishing",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        # Should not redirect to attacker site
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil-attacker.com", response.url)

    def test_redirect_allows_legitimate_twitter_subdomain(self):
        """Test that legitimate Twitter subdomains are allowed"""
        org = Organization.objects.create(
            name="Mobile Twitter Org",
            slug="mobile-twitter",
            url="https://mobile-twitter.com",
            twitter="https://mobile.twitter.com/testorg",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        # Should redirect to mobile.twitter.com
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://mobile.twitter.com/testorg")

    def test_redirect_blocks_double_dot_attack(self):
        """Test that ..twitter.com attack is blocked"""
        org = Organization.objects.create(
            name="Double Dot Attack",
            slug="double-dot",
            url="https://double-dot.com",
            twitter="https://evil..twitter.com/phishing",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        # Should not redirect
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil", response.url)

    def test_redirect_allows_x_com_for_twitter(self):
        """Test that x.com domain works for twitter platform"""
        org = Organization.objects.create(
            name="X Domain Org",
            slug="x-domain",
            url="https://x-domain.com",
            twitter="https://x.com/testorg",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://x.com/testorg")

    def test_redirect_blocks_evil_facebook_domain(self):
        """Test that non-Facebook domains are blocked"""
        org = Organization.objects.create(
            name="Evil FB Org",
            slug="evil-fb",
            url="https://evil-fb.com",
            facebook="https://phishing-site.com/steal-data",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "facebook"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("phishing-site.com", response.url)

    def test_redirect_allows_fb_com_shortdomain(self):
        """Test that fb.com short domain is allowed"""
        org = Organization.objects.create(
            name="FB Short Domain",
            slug="fb-short",
            url="https://fb-short.com",
            facebook="https://fb.com/testorg",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "facebook"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://fb.com/testorg")

    def test_redirect_blocks_evil_linkedin_domain(self):
        """Test that non-LinkedIn domains are blocked"""
        org = Organization.objects.create(
            name="Evil LI Org",
            slug="evil-li",
            url="https://evil-li.com",
            linkedin="https://fake-linkedin.com/company/phishing",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "linkedin"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("fake-linkedin.com", response.url)

    def test_redirect_allows_www_subdomains(self):
        """Test that www subdomains are allowed for all platforms"""
        org = Organization.objects.create(
            name="WWW Subdomains",
            slug="www-subdomains",
            url="https://www-test.com",
            twitter="https://www.twitter.com/testorg",
            facebook="https://www.facebook.com/testorg",
            linkedin="https://www.linkedin.com/company/testorg",
            social_clicks={},
        )

        # Test Twitter
        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://www.twitter.com/testorg")

        # Test Facebook
        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "facebook"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://www.facebook.com/testorg")

        # Test LinkedIn
        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "linkedin"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://www.linkedin.com/company/testorg")

    def test_concurrent_clicks_tracked_correctly(self):
        """Test that concurrent clicks are tracked atomically using threads"""
        import threading

        org = Organization.objects.create(
            name="Concurrent Clicks",
            slug="concurrent",
            url="https://concurrent.com",
            twitter="https://twitter.com/testorg",
            social_clicks={"twitter": 0},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})

        # Simulate 10 concurrent clicks using threads
        threads = []
        num_clicks = 10

        def click_link():
            # Each thread needs its own client instance
            from django.test import Client

            client = Client()
            client.get(url)

        for _ in range(num_clicks):
            thread = threading.Thread(target=click_link)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        org.refresh_from_db()
        # Should have incremented to 10 if atomic operations work correctly
        self.assertEqual(org.social_clicks.get("twitter", 0), num_clicks)
