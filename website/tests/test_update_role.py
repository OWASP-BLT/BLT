from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Domain, Organization, OrganizationAdmin

# Role constants matching OrganizationAdmin.role choices
ROLE_ADMIN = 0
ROLE_MODERATOR = 1
ROLE_DEACTIVATED = 9


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

        self.admin_user = User.objects.create_user(username="admin1", password="pass123")
        self.admin_record = OrganizationAdmin.objects.create(
            user=self.admin_user, organization=self.org, role=ROLE_ADMIN, is_active=True
        )

        self.mod_user = User.objects.create_user(username="mod1", password="pass123")
        self.mod_record = OrganizationAdmin.objects.create(
            user=self.mod_user,
            organization=self.org,
            role=ROLE_MODERATOR,
            is_active=True,
            domain=self.domain,
        )

        self.mod_user2 = User.objects.create_user(username="mod2", password="pass123")
        self.mod_record2 = OrganizationAdmin.objects.create(
            user=self.mod_user2,
            organization=self.org,
            role=ROLE_MODERATOR,
            is_active=True,
            domain=self.domain,
        )

    def test_get_request_rejected(self):
        """GET returns 'failed'."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.get(self.url)
        self.assertEqual(response.content.decode(), "failed")

    def test_unauthenticated_redirects(self):
        """Unauthenticated users are redirected."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

    def test_non_admin_user_rejected(self):
        """Users without OrganizationAdmin record are rejected."""
        regular = User.objects.create_user(username="regular", password="pass123")
        self.client.login(username="regular", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": "1"})
        self.assertEqual(response.content.decode(), "failed")

    def test_admin_deactivates_user(self):
        """Admin can deactivate a moderator."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": str(ROLE_DEACTIVATED)})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertFalse(self.mod_record.is_active)

    def test_admin_changes_role(self):
        """Admin can promote a moderator to admin."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": str(ROLE_ADMIN)})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.role, ROLE_ADMIN)
        self.assertTrue(self.mod_record.is_active)

    def test_admin_reactivates_deactivated_user(self):
        """Assigning an active role restores is_active."""
        self.mod_record.is_active = False
        self.mod_record.save()
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": str(ROLE_MODERATOR)})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertTrue(self.mod_record.is_active)

    def test_admin_sets_domain(self):
        """Admin can assign a domain to a user."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {
                "user@0": "mod1",
                "role@mod1": str(ROLE_MODERATOR),
                "domain@mod1": str(self.domain.pk),
            },
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.domain, self.domain)

    def test_admin_clears_domain(self):
        """Empty domain value clears the assignment."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {"user@0": "mod1", "role@mod1": str(ROLE_MODERATOR), "domain@mod1": ""},
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertIsNone(self.mod_record.domain)

    def test_domain_not_cleared_when_key_absent(self):
        """Domain preserved when domain@ key is absent."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": str(ROLE_MODERATOR)})
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.domain, self.domain)

    def test_self_modification_prevented(self):
        """Admins cannot modify their own role."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "admin1", "role@admin1": str(ROLE_DEACTIVATED)})
        self.assertEqual(response.content.decode(), "success")
        self.admin_record.refresh_from_db()
        self.assertTrue(self.admin_record.is_active)
        self.assertEqual(self.admin_record.role, ROLE_ADMIN)

    def test_multiple_users_batch_update(self):
        """Multiple users updated in a single request."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {
                "user@0": "mod1",
                "role@mod1": str(ROLE_ADMIN),
                "user@1": "mod2",
                "role@mod2": str(ROLE_DEACTIVATED),
            },
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.mod_record2.refresh_from_db()
        self.assertEqual(self.mod_record.role, ROLE_ADMIN)
        self.assertFalse(self.mod_record2.is_active)

    def test_duplicate_usernames_handled(self):
        """Duplicate usernames don't cause bulk_update errors."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(
            self.url,
            {"user@0": "mod1", "user@1": "mod1", "role@mod1": str(ROLE_ADMIN)},
        )
        self.assertEqual(response.content.decode(), "success")
        self.mod_record.refresh_from_db()
        self.assertEqual(self.mod_record.role, ROLE_ADMIN)

    def test_moderator_cannot_modify_admin(self):
        """Moderator cannot change an admin's role."""
        self.client.login(username="mod1", password="pass123")
        admin2 = User.objects.create_user(username="admin2", password="pass123")
        OrganizationAdmin.objects.create(
            user=admin2, organization=self.org, role=ROLE_ADMIN, is_active=True, domain=self.domain
        )
        response = self.client.post(self.url, {"user@0": "admin2", "role@admin2": str(ROLE_DEACTIVATED)})
        self.assertEqual(response.content.decode(), "success")
        admin2_record = OrganizationAdmin.objects.get(user=admin2)
        self.assertTrue(admin2_record.is_active)
        self.assertEqual(admin2_record.role, ROLE_ADMIN)

    def test_moderator_without_domain_rejected(self):
        """Moderator with no domain is rejected."""
        self.mod_record.domain = None
        self.mod_record.save()
        self.client.login(username="mod1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod2", "role@mod2": str(ROLE_DEACTIVATED)})
        self.assertEqual(response.content.decode(), "failed")

    def test_multiple_active_admins_rejected(self):
        """User with multiple active OrganizationAdmin records is rejected."""
        org2 = Organization.objects.create(name="Org 2", slug="org-2")
        OrganizationAdmin.objects.create(user=self.admin_user, organization=org2, role=ROLE_ADMIN, is_active=True)
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {"user@0": "mod1", "role@mod1": str(ROLE_DEACTIVATED)})
        self.assertEqual(response.content.decode(), "failed")

    def test_empty_post_returns_success(self):
        """POST with no user@ keys is a no-op success."""
        self.client.login(username="admin1", password="pass123")
        response = self.client.post(self.url, {})
        self.assertEqual(response.content.decode(), "success")
