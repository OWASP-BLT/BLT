"""
Tests for model __str__ methods.

This test file ensures that all models have properly functioning __str__ methods
that return readable strings for the Django admin and debugging purposes.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from website.models import (
    Bid,
    Contribution,
    Domain,
    Hunt,
    IP,
    Issue,
    IssueScreenshot,
    JoinRequest,
    Organization,
    OrganizationAdmin,
    OsshCommunity,
    Payment,
    Project,
    SecurityIncident,
    SecurityIncidentHistory,
    Subscription,
    Transaction,
    Wallet,
    Winner,
)


class ModelStrMethodTests(TestCase):
    """Test that __str__ methods return meaningful strings."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests."""
        cls.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        cls.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-org",
            url="https://test-org.com",
            admin=cls.user,
        )
        cls.domain = Domain.objects.create(
            name="test.com",
            url="https://test.com",
            organization=cls.organization,
        )

    def test_subscription_str(self):
        """Test Subscription __str__ method."""
        subscription = Subscription.objects.create(
            name="Premium",
            charge_per_month=99,
            hunt_per_domain=10,
            number_of_domains=5,
        )
        result = str(subscription)
        self.assertIn("Premium", result)
        self.assertIn("99", result)

    def test_join_request_str_pending(self):
        """Test JoinRequest __str__ method for pending requests."""
        join_request = JoinRequest.objects.create(
            team=self.organization,
            user=self.user,
            is_accepted=False,
        )
        result = str(join_request)
        self.assertIn("testuser", result)
        self.assertIn("Test Organization", result)
        self.assertIn("Pending", result)

    def test_join_request_str_accepted(self):
        """Test JoinRequest __str__ method for accepted requests."""
        join_request = JoinRequest.objects.create(
            team=self.organization,
            user=self.user,
            is_accepted=True,
        )
        result = str(join_request)
        self.assertIn("Accepted", result)

    def test_issue_screenshot_str(self):
        """Test IssueScreenshot __str__ method."""
        issue = Issue.objects.create(
            user=self.user,
            url="https://example.com/bug",
            description="Test issue",
            domain=self.domain,
        )
        screenshot = IssueScreenshot.objects.create(
            issue=issue,
            image="screenshots/test.png",
        )
        result = str(screenshot)
        self.assertIn("Screenshot", result)
        self.assertIn(str(issue.id), result)

    def test_winner_str(self):
        """Test Winner __str__ method."""
        hunt = Hunt.objects.create(
            name="Test Hunt",
            domain=self.domain,
            starts_on=timezone.now(),
            end_on=timezone.now() + timezone.timedelta(days=7),
        )
        winner = Winner.objects.create(
            hunt=hunt,
            winner=self.user,
        )
        result = str(winner)
        self.assertIn("testuser", result)
        self.assertIn("Test Hunt", result)

    def test_winner_str_no_winner(self):
        """Test Winner __str__ method when winner is not set."""
        hunt = Hunt.objects.create(
            name="Test Hunt 2",
            domain=self.domain,
            starts_on=timezone.now(),
            end_on=timezone.now() + timezone.timedelta(days=7),
        )
        winner = Winner.objects.create(
            hunt=hunt,
            winner=None,
        )
        result = str(winner)
        self.assertIn("TBD", result)

    def test_ip_str(self):
        """Test IP __str__ method."""
        ip = IP.objects.create(
            address="192.168.1.1",
            count=42,
            path="/api/test",
        )
        result = str(ip)
        self.assertIn("192.168.1.1", result)
        self.assertIn("42", result)

    def test_organization_admin_str(self):
        """Test OrganizationAdmin __str__ method."""
        org_admin = OrganizationAdmin.objects.create(
            user=self.user,
            organization=self.organization,
            role=0,  # Admin
        )
        result = str(org_admin)
        self.assertIn("testuser", result)
        self.assertIn("Admin", result)
        self.assertIn("Test Organization", result)

    def test_organization_admin_str_moderator(self):
        """Test OrganizationAdmin __str__ method for moderator role."""
        org_admin = OrganizationAdmin.objects.create(
            user=self.user,
            organization=self.organization,
            role=1,  # Moderator
        )
        result = str(org_admin)
        self.assertIn("Moderator", result)

    def test_wallet_str(self):
        """Test Wallet __str__ method."""
        wallet = Wallet.objects.create(
            user=self.user,
            current_balance=Decimal("100.50"),
        )
        result = str(wallet)
        self.assertIn("testuser", result)
        self.assertIn("100.50", result)

    def test_transaction_str_positive(self):
        """Test Transaction __str__ method for positive value."""
        wallet = Wallet.objects.create(
            user=self.user,
            current_balance=Decimal("100.00"),
        )
        transaction = Transaction.objects.create(
            wallet=wallet,
            value=Decimal("25.00"),
            running_balance=Decimal("125.00"),
        )
        result = str(transaction)
        self.assertIn("+", result)
        self.assertIn("25.00", result)

    def test_transaction_str_negative(self):
        """Test Transaction __str__ method for negative value."""
        wallet = Wallet.objects.create(
            user=self.user,
            current_balance=Decimal("100.00"),
        )
        transaction = Transaction.objects.create(
            wallet=wallet,
            value=Decimal("-10.00"),
            running_balance=Decimal("90.00"),
        )
        result = str(transaction)
        self.assertIn("-10.00", result)
        self.assertNotIn("+-", result)  # No double sign

    def test_payment_str_active(self):
        """Test Payment __str__ method for active payment."""
        wallet = Wallet.objects.create(
            user=self.user,
            current_balance=Decimal("100.00"),
        )
        payment = Payment.objects.create(
            wallet=wallet,
            value=Decimal("50.00"),
            active=True,
        )
        result = str(payment)
        self.assertIn("50.00", result)
        self.assertIn("Active", result)

    def test_payment_str_inactive(self):
        """Test Payment __str__ method for inactive payment."""
        wallet = Wallet.objects.create(
            user=self.user,
            current_balance=Decimal("100.00"),
        )
        payment = Payment.objects.create(
            wallet=wallet,
            value=Decimal("50.00"),
            active=False,
        )
        result = str(payment)
        self.assertIn("Inactive", result)

    def test_bid_str_with_user(self):
        """Test Bid __str__ method with user."""
        bid = Bid.objects.create(
            user=self.user,
            issue_url="https://github.com/org/repo/issues/123",
            amount_bch=Decimal("0.5"),
            status="Open",
        )
        result = str(bid)
        self.assertIn("testuser", result)
        self.assertIn("0.5", result)
        self.assertIn("BCH", result)
        self.assertIn("Open", result)

    def test_bid_str_with_github_username(self):
        """Test Bid __str__ method with GitHub username instead of user."""
        bid = Bid.objects.create(
            user=None,
            github_username="github_contributor",
            issue_url="https://github.com/org/repo/issues/123",
            amount_bch=Decimal("1.0"),
            status="Closed",
        )
        result = str(bid)
        self.assertIn("github_contributor", result)

    def test_contribution_str(self):
        """Test Contribution __str__ method."""
        project = Project.objects.create(
            name="Test Project",
            slug="test-project",
        )
        contribution = Contribution.objects.create(
            user=self.user,
            title="Fix critical bug in authentication module",
            description="Fixed XSS vulnerability",
            repository=project,
            contribution_type="pull_request",
            created=timezone.now(),
            status="open",
        )
        result = str(contribution)
        self.assertIn("Fix critical bug", result)
        self.assertIn("pull_request", result)

    def test_contribution_str_truncation(self):
        """Test that long Contribution titles are truncated."""
        project = Project.objects.create(
            name="Test Project 2",
            slug="test-project-2",
        )
        long_title = "A" * 100  # Very long title
        contribution = Contribution.objects.create(
            user=self.user,
            title=long_title,
            description="Description",
            repository=project,
            contribution_type="commit",
            created=timezone.now(),
            status="closed",
        )
        result = str(contribution)
        # Should be truncated to 50 chars
        self.assertLessEqual(len(result.split(" (")[0]), 50)

    def test_ossh_community_str(self):
        """Test OsshCommunity __str__ method."""
        community = OsshCommunity.objects.create(
            name="Open Source Security Hub",
            website="https://ossh.example.com",
            source="GitHub",
            category="community",
        )
        result = str(community)
        self.assertIn("Open Source Security Hub", result)
        self.assertIn("community", result)

    def test_security_incident_str(self):
        """Test SecurityIncident __str__ method."""
        incident = SecurityIncident.objects.create(
            title="Data Breach Alert",
            description="Unauthorized access detected",
            severity="high",
            status="investigating",
            reporter=self.user,
        )
        result = str(incident)
        self.assertIn("Data Breach Alert", result)
        self.assertIn("High", result)  # Display value from get_severity_display

    def test_security_incident_history_str(self):
        """Test SecurityIncidentHistory __str__ method."""
        incident = SecurityIncident.objects.create(
            title="Test Incident",
            description="Test description",
            severity="medium",
            status="open",
            reporter=self.user,
        )
        history = SecurityIncidentHistory.objects.create(
            incident=incident,
            field_name="status",
            old_value="open",
            new_value="investigating",
            changed_by=self.user,
        )
        result = str(history)
        self.assertIn("status", result)
        self.assertIn("testuser", result)

    def test_security_incident_history_str_system(self):
        """Test SecurityIncidentHistory __str__ when changed_by is None."""
        incident = SecurityIncident.objects.create(
            title="Test Incident 2",
            description="Test description",
            severity="low",
            status="open",
            reporter=self.user,
        )
        history = SecurityIncidentHistory.objects.create(
            incident=incident,
            field_name="severity",
            old_value="low",
            new_value="medium",
            changed_by=None,
        )
        result = str(history)
        self.assertIn("System", result)
