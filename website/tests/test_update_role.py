from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Domain, Organization, OrganizationAdmin


class UpdateRoleTests(TestCase):
    """Tests for the update_role view (batch admin role updates)."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("update-role")

        self.org = Organization.objects.create(name="Test Org", slug="test-org")
        self.domain = Domain.objects.create(
            name="example.com",
            url="https://example.com",
            organization=self.org,
        )

        # Admin user (role=0)
        self.admin_user = User.objects.create_user(username="admin1", password="pass123")
        self.admin_record = OrganizationAdmin.objects.create(
            user=self.admin_user, organization=self.org, role=0, is_active=True
        )

        # Target moderator user (role=1)
        self.mod_user = User.objects.create_user(username="mod1", password="pass123")
        self.mod_record = OrganizationAdmin.objects.create(
            user=self.mod_user, organization=self.org, role=1, is_active=True, domain=self.domain
        )

        # Another target user (role=1)
        self.mod_user2 = User.objects.create_user(username="mod2", password="pass123")
        self.mod_record2 = OrganizationAdmin.objects.create(
            user=self.mod_user2, organization=self.org, role=1, is_active=True, domain=self.domain
        )

    def test_get_request_rejected(self):
        """GET requests should return 'failed'."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.get(self.url)
        self.assertEqual(response.content.decode(), "failed")

    def test_unauthenticated_redirects(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

    def test_non_admin_user_rejected(self):
        """Users without an OrganizationAdmin record should fail."""
        regular = User.objects.create_user(username="regular", password="pass123")
        self.client.login(username="regular", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "1"})
        self.assertEqual(response.content.decode(), "failed")

    def test_admin_deactivates_user(self):
        """Admin (role=0) can deactivate a moderator with role=9."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "9"})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertFalse(self.mod_record.is_active)

    def test_admin_changes_role(self):
        """Admin (role=0) can change a moderator's role to admin."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "0"})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.role, 0)
        self.assertTrue(self.mod_record.is_active)

    def test_admin_reactivates_deactivated_user(self):
        """Assigning role 0 or 1 should restore is_active=True."""
        self.mod_record.is_active = False
        self.mod_record.save()
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "1"})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertTrue(self.mod_record.is_active)

    def test_admin_sets_domain(self):
        """Admin (role=0) can assign a domain to a user."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {
                "user@0": "mod1",
                "role@mod1": "1",
                "domain@mod1": str(self.domain.pk),
            },
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.domain, self.domain)

    def test_admin_clears_domain(self):
        """Admin (role=0) can clear a user's domain by sending empty value."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {"user@0": "mod1", "role@mod1": "1", "domain@mod1": ""},
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertIsNone(self.mod_record.domain)

    def test_domain_not_cleared_when_key_absent(self):
        """Domain should not be cleared when domain@ key is absent from POST."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "1"})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.domain, self.domain)

    def test_self_modification_prevented(self):
        """Admins cannot modify their own role."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "admin1", "role@admin1": "9"})
        self.assertEqual(response.content.decode(), "success")
        self.admin_record.refresh_from_db()
        # Should remain unchanged
        self.assertTrue(self.admin_record.is_active)
        self.assertEqual(self.admin_record.role, 0)

    def test_multiple_users_batch_update(self):
        """Multiple users can be updated in a single request."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {
                "user@0": "mod1",
                "role@mod1": "0",
                "user@1": "mod2",
                "role@mod2": "9",
            },
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.mod_record2.refresh_from_db()
        self.assertEqual(self.mod_record.role, 0)
        self.assertFalse(self.mod_record2.is_active)

    def test_duplicate_usernames_handled(self):
        """Duplicate usernames in POST should not cause bulk_update errors."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {"user@0": "mod1", "user@1": "mod1", "role@mod1": "0"},
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.role, 0)

    def test_moderator_cannot_modify_admin(self):
        """Moderator (role=1) cannot deactivate or change an admin (role=0)."""
        self.client.login(username="mod1", password="pass123")
        # Create another admin to target
        admin2 = User.objects.create_user(username="admin2", password="pass123")
        OrganizationAdmin.objects.create(user=admin2, organization=self.org, role=0, is_active=True, domain=self.domain)
        response = self.client.post(self.url, {"user@0": "admin2", "role@admin2": "9"})
        self.assertEqual(response.content.decode(), "success")
        admin2_record = OrganizationAdmin.objects.get(user=admin2)
        # Admin should remain unchanged
        self.assertTrue(admin2_record.is_active)
        self.assertEqual(admin2_record.role, 0)

    def test_moderator_without_domain_rejected(self):
        """Moderator with no domain assigned should fail."""
        self.mod_record.domain = None
        self.mod_record.save()
        self.client.login(username="mod1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod2", "role@mod2": "9"})
        self.assertEqual(response.content.decode(), "failed")

    def test_multiple_active_admins_rejected(self):
        """User with multiple active OrganizationAdmin records should fail."""
        org2 = Organization.objects.create(name="Org 2", slug="org-2")
        OrganizationAdmin.objects.create(user=self.admin_user, organization=org2, role=0, is_active=True)
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "9"})
        self.assertEqual(response.content.decode(), "failed")

    def test_empty_post_returns_success(self):
        """POST with no user@ keys should return success (no-op)."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {})
        self.assertEqual(response.content.decode(), "success")
