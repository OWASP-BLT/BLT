from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Recommendation, RecommendationRequest, RecommendationSkill


class RecommendationTestCase(TestCase):
    """Test cases for the recommendation functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test users
        self.user1 = User.objects.create_user(username="testuser1", email="test1@example.com", password="testpass123")
        self.user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")
        self.user3 = User.objects.create_user(username="testuser3", email="test3@example.com", password="testpass123")

        # UserProfile is created automatically by signal
        # Create test skills
        self.skill1 = RecommendationSkill.objects.create(name="Python", category="technical")
        self.skill2 = RecommendationSkill.objects.create(name="Django", category="technical")
        self.skill3 = RecommendationSkill.objects.create(name="Communication", category="soft_skills")

        # Create test client
        self.client = Client()

    def test_add_recommendation_authenticated(self):
        """Test adding a recommendation with an authenticated user."""
        self.client.login(username="testuser1", password="testpass123")

        data = {
            "relationship": "colleague",
            "recommendation_text": "Test user 2 is an excellent developer with great problem-solving skills. "
            * 10,  # 200+ chars
            "skills_endorsed": [self.skill1.name, self.skill2.name],
        }

        response = self.client.post(reverse("add_recommendation", kwargs={"username": self.user2.username}), data)

        # Should redirect to profile after successful creation
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("profile", kwargs={"slug": self.user2.username}))

        # Check that recommendation was created
        self.assertEqual(Recommendation.objects.count(), 1)
        recommendation = Recommendation.objects.first()
        self.assertEqual(recommendation.from_user, self.user1)
        self.assertEqual(recommendation.to_user, self.user2)
        self.assertEqual(recommendation.relationship, "colleague")
        self.assertFalse(recommendation.is_approved)  # Should be pending approval

    def test_add_recommendation_unauthenticated(self):
        """Test that unauthenticated users cannot add recommendations."""
        data = {
            "relationship": "colleague",
            "recommendation_text": "Test recommendation text. " * 10,
            "skills_endorsed": [],
        }

        response = self.client.post(reverse("add_recommendation", kwargs={"username": self.user2.username}), data)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

        # No recommendation should be created
        self.assertEqual(Recommendation.objects.count(), 0)

    def test_self_recommendation_prevented(self):
        """Test that users cannot recommend themselves."""
        self.client.login(username="testuser1", password="testpass123")

        data = {
            "relationship": "colleague",
            "recommendation_text": "I am great. " * 20,
            "skills_endorsed": [],
        }

        response = self.client.post(reverse("add_recommendation", kwargs={"username": self.user1.username}), data)

        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 0)

    def test_approve_recommendation(self):
        """Test that recipient can approve a recommendation."""
        self.client.login(username="testuser1", password="testpass123")

        # Create a recommendation
        recommendation = Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="Great developer. " * 15,
            skills_endorsed=["Python"],
        )

        # Log in as recipient
        self.client.logout()
        self.client.login(username="testuser2", password="testpass123")

        # Approve the recommendation
        response = self.client.post(
            reverse("approve_recommendation", kwargs={"recommendation_id": recommendation.id}),
            {"action": "approve"},
        )

        self.assertEqual(response.status_code, 302)
        recommendation.refresh_from_db()
        self.assertTrue(recommendation.is_approved)
        self.assertTrue(recommendation.is_visible)

    def test_delete_pending_recommendation(self):
        """Test that recommender can delete a pending recommendation."""
        self.client.login(username="testuser1", password="testpass123")

        # Create a pending recommendation
        recommendation = Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="Test recommendation. " * 15,
        )

        # Delete the recommendation
        response = self.client.post(reverse("delete_recommendation", kwargs={"recommendation_id": recommendation.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 0)

    def test_cannot_delete_approved_recommendation(self):
        """Test that approved recommendations cannot be deleted."""
        self.client.login(username="testuser1", password="testpass123")

        # Create and approve a recommendation
        recommendation = Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="Test recommendation. " * 15,
            is_approved=True,
            is_visible=True,
        )

        # Try to delete (should fail)
        response = self.client.post(reverse("delete_recommendation", kwargs={"recommendation_id": recommendation.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Recommendation.objects.count(), 1)  # Still exists

    def test_request_recommendation(self):
        """Test requesting a recommendation from another user."""
        self.client.login(username="testuser1", password="testpass123")

        data = {"message": "Please write me a recommendation."}

        response = self.client.post(reverse("request_recommendation", kwargs={"username": self.user2.username}), data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(RecommendationRequest.objects.count(), 1)
        request = RecommendationRequest.objects.first()
        self.assertEqual(request.from_user, self.user1)
        self.assertEqual(request.to_user, self.user2)
        self.assertEqual(request.status, "pending")

    def test_respond_to_request_accept(self):
        """Test accepting a recommendation request."""
        # Create a request
        request = RecommendationRequest.objects.create(
            from_user=self.user1, to_user=self.user2, message="Please recommend me"
        )

        # Log in as recipient
        self.client.login(username="testuser2", password="testpass123")

        # Accept the request
        response = self.client.post(
            reverse("respond_to_request", kwargs={"request_id": request.id}), {"action": "accept"}
        )

        self.assertEqual(response.status_code, 302)
        request.refresh_from_db()
        self.assertEqual(request.status, "accepted")

    def test_respond_to_request_decline(self):
        """Test declining a recommendation request."""
        # Create a request
        request = RecommendationRequest.objects.create(
            from_user=self.user1, to_user=self.user2, message="Please recommend me"
        )

        # Log in as recipient
        self.client.login(username="testuser2", password="testpass123")

        # Decline the request
        response = self.client.post(
            reverse("respond_to_request", kwargs={"request_id": request.id}), {"action": "decline"}
        )

        self.assertEqual(response.status_code, 302)
        request.refresh_from_db()
        self.assertEqual(request.status, "declined")

    def test_cancel_request(self):
        """Test that sender can cancel a pending request."""
        # Create a request
        request = RecommendationRequest.objects.create(
            from_user=self.user1, to_user=self.user2, message="Please recommend me"
        )

        # Log in as sender
        self.client.login(username="testuser1", password="testpass123")

        # Cancel the request
        response = self.client.post(
            reverse("respond_to_request", kwargs={"request_id": request.id}), {"action": "cancel"}
        )

        self.assertEqual(response.status_code, 302)
        request.refresh_from_db()
        self.assertEqual(request.status, "cancelled")

    def test_edit_pending_recommendation(self):
        """Test editing a pending recommendation."""
        self.client.login(username="testuser1", password="testpass123")

        # Create a pending recommendation
        recommendation = Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="Original text. " * 15,
        )

        # Edit the recommendation
        data = {
            "relationship": "mentor",
            "recommendation_text": "Updated recommendation text. " * 10,
            "skills_endorsed": [self.skill1.name],
        }

        response = self.client.post(
            reverse("edit_recommendation", kwargs={"recommendation_id": recommendation.id}), data
        )

        self.assertEqual(response.status_code, 302)
        recommendation.refresh_from_db()
        self.assertEqual(recommendation.relationship, "mentor")
        self.assertIn(self.skill1.name, recommendation.skills_endorsed)

    def test_highlight_recommendation(self):
        """Test highlighting a recommendation."""
        # Create and approve a recommendation
        recommendation = Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="Great developer. " * 15,
            is_approved=True,
            is_visible=True,
        )

        # Log in as recipient
        self.client.login(username="testuser2", password="testpass123")

        # Highlight the recommendation
        response = self.client.post(
            reverse("highlight_recommendation", kwargs={"recommendation_id": recommendation.id}),
            {"is_highlighted": True},
        )

        self.assertEqual(response.status_code, 302)
        recommendation.refresh_from_db()
        self.assertTrue(recommendation.is_highlighted)

    def test_edit_recommendation_blurb(self):
        """Test editing the recommendation blurb on profile."""
        self.client.login(username="testuser1", password="testpass123")

        data = {"recommendation_blurb": "I am a skilled developer with expertise in Python and Django."}

        response = self.client.post(reverse("edit_recommendation_blurb"), data)

        self.assertEqual(response.status_code, 302)
        self.user1.userprofile.refresh_from_db()
        self.assertEqual(self.user1.userprofile.recommendation_blurb, data["recommendation_blurb"])

    def test_profile_displays_recommendations(self):
        """Test that profile page displays recommendations correctly."""
        # Create an approved recommendation
        Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="Great developer. " * 15,
            is_approved=True,
            is_visible=True,
        )

        # View profile
        response = self.client.get(reverse("profile", kwargs={"slug": self.user2.username}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Great developer")

    def test_duplicate_recommendation_prevented(self):
        """Test that duplicate recommendations are prevented."""
        self.client.login(username="testuser1", password="testpass123")

        # Create first recommendation
        Recommendation.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            relationship="colleague",
            recommendation_text="First recommendation. " * 15,
            is_approved=True,
        )

        # Try to create duplicate
        data = {
            "relationship": "mentor",
            "recommendation_text": "Second recommendation. " * 15,
            "skills_endorsed": [],
        }

        response = self.client.post(reverse("add_recommendation", kwargs={"username": self.user2.username}), data)

        # Should redirect with warning
        self.assertEqual(response.status_code, 302)
        # Only one recommendation should exist
        self.assertEqual(Recommendation.objects.filter(from_user=self.user1, to_user=self.user2).count(), 1)
