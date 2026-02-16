import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Bid


class BiddingTestCase(TestCase):
    """Test cases for the bidding functionality."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")

        # Create a test client
        self.client = Client()

        # Define test data
        self.valid_github_issue_url = "https://github.com/OWASP-BLT/BLT-Website/issues/123"
        self.invalid_github_issue_url = "https://example.com/not-a-github-issue"
        self.bid_amount = "5.0"

    def test_add_bid_authenticated_user(self):
        """Test adding a bid with an authenticated user."""
        # Log in the user
        self.client.login(username="testuser", password="testpassword")

        # Make a POST request to the bidding endpoint
        response = self.client.post(
            reverse("BiddingData"),
            {"issue_url": self.valid_github_issue_url, "bid_amount": self.bid_amount, "user": self.user.username},
            follow=True,  # Follow redirects
        )

        # Check that the response is successful after redirect
        self.assertEqual(response.status_code, 200)

        # Check that a bid was created in the database
        self.assertEqual(Bid.objects.count(), 1)

        # Check that the bid has the correct data
        bid = Bid.objects.first()
        self.assertEqual(bid.user, self.user)
        self.assertEqual(bid.issue_url, self.valid_github_issue_url)
        self.assertEqual(bid.amount_bch, Decimal(self.bid_amount))
        self.assertEqual(bid.status, "Open")

    def test_add_bid_unauthenticated_user(self):
        """Test adding a bid with an unauthenticated user."""
        # Make a POST request to the bidding endpoint without logging in
        response = self.client.post(
            reverse("BiddingData"),
            {"issue_url": self.valid_github_issue_url, "bid_amount": self.bid_amount, "user": self.user.username},
            follow=True,  # Follow redirects
        )

        # Check that the user is redirected to the login page
        self.assertEqual(response.status_code, 200)  # After following redirects
        self.assertIn("/accounts/login/", response.redirect_chain[0][0])  # Check redirect URL

        # Check that no bid was created
        self.assertEqual(Bid.objects.count(), 0)

    def test_add_bid_with_github_username(self):
        """Test adding a bid with a GitHub username that doesn't match a user in the system."""
        # Log in the user
        self.client.login(username="testuser", password="testpassword")

        # Make a POST request with a different GitHub username
        github_username = "github_user"
        response = self.client.post(
            reverse("BiddingData"),
            {"issue_url": self.valid_github_issue_url, "bid_amount": self.bid_amount, "user": github_username},
            follow=True,  # Follow redirects
        )

        # Check that the response is successful after redirect
        self.assertEqual(response.status_code, 200)

        # Check that a bid was created
        self.assertEqual(Bid.objects.count(), 1)

        # Check that the bid has the correct data
        bid = Bid.objects.first()
        self.assertEqual(bid.user, self.user)  # The authenticated user should be set as the fallback
        self.assertEqual(bid.github_username, github_username)
        self.assertEqual(bid.issue_url, self.valid_github_issue_url)
        self.assertEqual(bid.amount_bch, Decimal(self.bid_amount))

    def test_view_bidding_page(self):
        """Test that the bidding page can be viewed successfully."""
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse("BiddingData"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bidding.html")

    def test_add_bid_without_authentication(self):
        """Test that a bid can be added without authentication, using just a GitHub username."""
        # Logout to ensure we're testing as an unauthenticated user
        self.client.logout()

        # Initial count of bids
        initial_bid_count = Bid.objects.count()

        # Post data for creating a bid
        response = self.client.post(
            reverse("BiddingData"),
            {
                "user": "github_user_123",
                "issue_url": self.valid_github_issue_url,
                "bid_amount": self.bid_amount,
            },
            follow=True,
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Check that we were redirected to the login page
        self.assertIn("/accounts/login/", response.redirect_chain[0][0])

        # Verify no new bid was created (since unauthenticated users are redirected to login)
        self.assertEqual(Bid.objects.count(), initial_bid_count)

    def test_add_bid_with_github_url_in_profile(self):
        """Test that a bid can be added using the GitHub username from the user's profile."""
        # Login the user
        self.client.login(username="testuser", password="testpassword")

        # Set GitHub URL in the user's profile
        user = User.objects.get(username="testuser")
        user.userprofile.github_url = "https://github.com/profile_github_user"
        user.userprofile.save()

        # Initial count of bids
        initial_bid_count = Bid.objects.count()

        # Post data for creating a bid without specifying a username
        response = self.client.post(
            reverse("BiddingData"),
            {
                "user": "",  # Empty username to test extraction from profile
                "issue_url": self.valid_github_issue_url,
                "bid_amount": self.bid_amount,
            },
            follow=True,
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify a new bid was created
        self.assertEqual(Bid.objects.count(), initial_bid_count + 1)

        # Get the newly created bid
        new_bid = Bid.objects.latest("created")

        # Verify bid details
        self.assertEqual(new_bid.user, user)  # User should be set to the authenticated user
        self.assertEqual(new_bid.github_username, "profile_github_user")  # GitHub username extracted from profile URL
        self.assertEqual(new_bid.issue_url, self.valid_github_issue_url)
        self.assertEqual(float(new_bid.amount_bch), float(self.bid_amount))
        self.assertEqual(new_bid.status, "Open")


class ChangeBidStatusTests(TestCase):
    """Test cases for the change_bid_status view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="bidder", password="testpass")
        self.bid = Bid.objects.create(
            user=self.user,
            issue_url="https://github.com/OWASP-BLT/BLT/issues/1",
            status="Open",
        )

    def test_unauthenticated_post_redirects(self):
        """Unauthenticated POST to change_bid_status should redirect to login."""
        response = self.client.post(
            reverse("change_bid_status"),
            json.dumps({"id": self.bid.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_authenticated_changes_status(self):
        """Authenticated POST should change bid status to Selected."""
        self.client.login(username="bidder", password="testpass")
        response = self.client.post(
            reverse("change_bid_status"),
            json.dumps({"id": self.bid.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.bid.refresh_from_db()
        self.assertEqual(self.bid.status, "Selected")

    def test_nonexistent_bid_returns_error(self):
        """POST with invalid bid ID should return error."""
        self.client.login(username="bidder", password="testpass")
        response = self.client.post(
            reverse("change_bid_status"),
            json.dumps({"id": 99999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])

    def test_get_request_returns_405(self):
        """GET request should return 405 Method Not Allowed."""
        self.client.login(username="bidder", password="testpass")
        response = self.client.get(reverse("change_bid_status"))
        self.assertEqual(response.status_code, 405)


class GetUniqueIssuesTests(TestCase):
    """Test cases for the get_unique_issues view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser2", password="testpass")
        self.bid = Bid.objects.create(
            user=self.user,
            issue_url="https://github.com/OWASP-BLT/BLT/issues/42",
            status="Open",
        )

    def test_returns_bids_for_issue(self):
        """POST with valid issue_url should return matching bids."""
        response = self.client.post(
            reverse("get_unique_issues"),
            json.dumps({"issue_url": "https://github.com/OWASP-BLT/BLT/issues/42"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)

    def test_missing_issue_url_returns_error(self):
        """POST without issue_url should return error."""
        response = self.client.post(
            reverse("get_unique_issues"),
            json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])

    def test_get_request_returns_405(self):
        """GET request should return 405 Method Not Allowed."""
        response = self.client.get(reverse("get_unique_issues"))
        self.assertEqual(response.status_code, 405)

    def test_invalid_json_returns_error(self):
        """POST with invalid JSON should return error."""
        response = self.client.post(
            reverse("get_unique_issues"),
            "not valid json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
