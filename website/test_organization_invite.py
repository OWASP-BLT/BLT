"""
Tests for organization invite functionality
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import InviteOrganization


class OrganizationInviteTestCase(TestCase):
    """Test organization invite system"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.invite_url = reverse("invite")
        self.register_org_url = reverse("register_organization")

    def test_invite_page_accessible_without_login(self):
        """Test that invite page is accessible to non-logged-in users"""
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 200)

    def test_invite_page_accessible_with_login(self):
        """Test that invite page is accessible to logged-in users"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 200)

    def test_logged_in_user_creates_invite_record(self):
        """Test that logged-in users create InviteOrganization records"""
        self.client.login(username="testuser", password="testpass123")

        # Submit invite form
        response = self.client.post(
            self.invite_url,
            {"email": "org@company.com", "organization_name": "Test Company"},
        )

        self.assertEqual(response.status_code, 200)

        # Check that invite record was created
        invite = InviteOrganization.objects.filter(sender=self.user, email="org@company.com").first()
        self.assertIsNotNone(invite)
        self.assertEqual(invite.organization_name, "Test Company")
        self.assertIsNotNone(invite.referral_code)
        self.assertFalse(invite.points_awarded)

    def test_non_logged_in_user_no_invite_record(self):
        """Test that non-logged-in users don't create InviteOrganization records"""
        # Submit invite form without login
        response = self.client.post(
            self.invite_url,
            {"email": "org@company.com", "organization_name": "Test Company"},
        )

        self.assertEqual(response.status_code, 200)

        # Check that no invite record was created
        invite_count = InviteOrganization.objects.filter(email="org@company.com").count()
        self.assertEqual(invite_count, 0)

    def test_referral_code_stored_in_session(self):
        """Test that referral code is stored in session when visiting org registration"""
        # Create an invite
        invite = InviteOrganization.objects.create(
            sender=self.user, email="org@company.com", organization_name="Test Company"
        )

        # Visit organization registration with referral code
        response = self.client.get(f"{self.register_org_url}?ref={invite.referral_code}")

        self.assertEqual(response.status_code, 200)
        # Check that referral code is in session
        self.assertEqual(self.client.session.get("org_ref"), str(invite.referral_code))

    def test_organization_registration_awards_points(self):
        """Test that registering an organization via referral link awards 5 points"""
        from website.models import Organization, Points

        # Create an invite
        invite = InviteOrganization.objects.create(
            sender=self.user, email="org@company.com", organization_name="Test Company"
        )

        # Create another user to register the organization
        User.objects.create_user(username="orgadmin", email="admin@company.com", password="testpass123")
        self.client.login(username="orgadmin", password="testpass123")

        # Visit registration page with referral code
        self.client.get(f"{self.register_org_url}?ref={invite.referral_code}")

        # Register organization
        self.client.post(
            self.register_org_url,
            {
                "organization_name": "Test Company",
                "organization_url": "https://testcompany.com",
                "support_email": "support@testcompany.com",
                "email": "admin@company.com",
            },
        )

        # Check that organization was created
        organization = Organization.objects.filter(name="Test Company").first()
        self.assertIsNotNone(organization)

        # Check that points were awarded
        points = Points.objects.filter(user=self.user, score=5).first()
        self.assertIsNotNone(points)
        self.assertIn("Organization invite referral", points.reason)

        # Check that invite was updated
        invite.refresh_from_db()
        self.assertTrue(invite.points_awarded)
        self.assertEqual(invite.organization, organization)

    def test_organization_registration_without_referral_no_points(self):
        """Test that registering without referral doesn't award points"""
        from website.models import Organization, Points

        # Create user to register organization
        User.objects.create_user(username="orgadmin", email="admin@company.com", password="testpass123")
        self.client.login(username="orgadmin", password="testpass123")

        # Register organization without referral
        self.client.post(
            self.register_org_url,
            {
                "organization_name": "Test Company",
                "organization_url": "https://testcompany.com",
                "support_email": "support@testcompany.com",
                "email": "admin@company.com",
            },
        )

        # Check that organization was created
        organization = Organization.objects.filter(name="Test Company").first()
        self.assertIsNotNone(organization)

        # Check that no points were awarded
        points_count = Points.objects.filter(score=5).count()
        self.assertEqual(points_count, 0)

    def test_duplicate_referral_usage_no_double_points(self):
        """Test that using the same referral code twice doesn't award points twice"""
        from website.models import Points

        # Create an invite
        invite = InviteOrganization.objects.create(
            sender=self.user, email="org@company.com", organization_name="Test Company"
        )

        # Create first organization with referral
        User.objects.create_user(username="orgadmin1", email="admin1@company.com", password="testpass123")
        self.client.login(username="orgadmin1", password="testpass123")
        self.client.get(f"{self.register_org_url}?ref={invite.referral_code}")
        self.client.post(
            self.register_org_url,
            {
                "organization_name": "Test Company 1",
                "organization_url": "https://testcompany1.com",
                "support_email": "support@testcompany1.com",
                "email": "admin1@company.com",
            },
        )

        # Try to create second organization with same referral
        User.objects.create_user(username="orgadmin2", email="admin2@company.com", password="testpass123")
        self.client.login(username="orgadmin2", password="testpass123")
        self.client.get(f"{self.register_org_url}?ref={invite.referral_code}")
        self.client.post(
            self.register_org_url,
            {
                "organization_name": "Test Company 2",
                "organization_url": "https://testcompany2.com",
                "support_email": "support@testcompany2.com",
                "email": "admin2@company.com",
            },
        )

        # Check that only one set of points was awarded
        points_count = Points.objects.filter(user=self.user, score=5).count()
        self.assertEqual(points_count, 1)

    def test_invalid_referral_code_no_points(self):
        """Test that invalid referral codes don't award points"""
        from website.models import Organization, Points

        # Create user to register organization
        User.objects.create_user(username="orgadmin", email="admin@company.com", password="testpass123")
        self.client.login(username="orgadmin", password="testpass123")

        # Visit registration page with invalid referral code
        self.client.get(f"{self.register_org_url}?ref=invalid-code-123")

        # Register organization
        self.client.post(
            self.register_org_url,
            {
                "organization_name": "Test Company",
                "organization_url": "https://testcompany.com",
                "support_email": "support@testcompany.com",
                "email": "admin@company.com",
            },
        )

        # Check that organization was created
        organization = Organization.objects.filter(name="Test Company").first()
        self.assertIsNotNone(organization)

        # Check that no points were awarded
        points_count = Points.objects.filter(score=5).count()
        self.assertEqual(points_count, 0)


class InviteOrganizationModelTestCase(TestCase):
    """Test InviteOrganization model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_invite_creation(self):
        """Test creating an invite"""
        invite = InviteOrganization.objects.create(
            sender=self.user, email="org@company.com", organization_name="Test Company"
        )

        self.assertEqual(invite.sender, self.user)
        self.assertEqual(invite.email, "org@company.com")
        self.assertEqual(invite.organization_name, "Test Company")
        self.assertIsNotNone(invite.referral_code)
        self.assertFalse(invite.points_awarded)
        self.assertIsNone(invite.organization)

    def test_referral_code_is_unique(self):
        """Test that referral codes are unique"""
        invite1 = InviteOrganization.objects.create(
            sender=self.user, email="org1@company.com", organization_name="Company 1"
        )
        invite2 = InviteOrganization.objects.create(
            sender=self.user, email="org2@company.com", organization_name="Company 2"
        )

        self.assertNotEqual(invite1.referral_code, invite2.referral_code)

    def test_invite_string_representation(self):
        """Test string representation of invite"""
        invite = InviteOrganization.objects.create(
            sender=self.user, email="org@company.com", organization_name="Test Company"
        )

        expected = f"Organization invite from {self.user} to org@company.com"
        self.assertEqual(str(invite), expected)
