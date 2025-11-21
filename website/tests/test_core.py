import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import ForumCategory, ForumPost, GitHubIssue, Organization, Project, Repo, UserProfile


class ForumTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.category = ForumCategory.objects.create(name="Test Category", description="Test Description")
        self.client.login(username="testuser", password="testpass")

        self.post_data = {"title": "Test Post", "category": self.category.id, "description": "Test Description"}

    def test_create_and_view_forum_post(self):
        # Create a new forum post
        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(self.post_data), content_type="application/json"
        )

        # Check if post was created successfully
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify post exists in database
        post = ForumPost.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.title, self.post_data["title"])
        self.assertEqual(post.description, self.post_data["description"])
        self.assertEqual(post.category_id, self.post_data["category"])
        self.assertEqual(post.user, self.user)

        # View the forum page
        response = self.client.get(reverse("view_forum"))

        # Check if page loads successfully
        self.assertEqual(response.status_code, 200)

        # Check if our post is in the context
        self.assertIn("posts", response.context)
        self.assertIn(post, response.context["posts"])

        # Check if post content is in the response
        self.assertContains(response, self.post_data["title"])
        self.assertContains(response, self.post_data["description"])

    def test_forum_post_voting(self):
        # Create a test post first
        post = ForumPost.objects.create(
            user=self.user, title="Test Post for Voting", description="Test Description", category=self.category
        )

        # Test upvoting
        response = self.client.post(
            reverse("vote_forum_post"),
            data=json.dumps({"post_id": post.id, "up_vote": True, "down_vote": False}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["up_vote"], 1)
        self.assertEqual(data["down_vote"], 0)

        # Test downvoting
        response = self.client.post(
            reverse("vote_forum_post"),
            data=json.dumps({"post_id": post.id, "up_vote": False, "down_vote": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["up_vote"], 0)
        self.assertEqual(data["down_vote"], 1)

        # Verify vote counts in database
        post.refresh_from_db()
        self.assertEqual(post.up_votes, 0)
        self.assertEqual(post.down_votes, 1)

    def test_forum_post_commenting(self):
        # Create a test post first
        post = ForumPost.objects.create(
            user=self.user, title="Test Post for Comments", description="Test Description", category=self.category
        )

        # Test adding a comment
        comment_data = {"post_id": post.id, "content": "Test comment content"}

        response = self.client.post(
            reverse("add_forum_comment"), data=json.dumps(comment_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify comment exists in database
        self.assertEqual(post.comments.count(), 1)
        comment = post.comments.first()
        self.assertEqual(comment.content, comment_data["content"])
        self.assertEqual(comment.user, self.user)

        # View the forum page and check if comment is displayed
        response = self.client.get(reverse("view_forum"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, comment_data["content"])

    def test_forum_post_with_repo_link(self):
        # Create a test repo
        repo = Repo.objects.create(
            name="Test Repo", description="Test repo desc", repo_url="https://github.com/test/repo"
        )

        # Create a forum post with repo link
        post_data = {
            "title": "Test Post with Repo",
            "category": self.category.id,
            "description": "Test Description with repo link",
            "repo": repo.id,
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify post has repo link
        post = ForumPost.objects.first()
        self.assertIsNotNone(post.repo)
        self.assertEqual(post.repo.id, repo.id)

    def test_forum_post_with_project_link(self):
        # Create a test project
        project = Project.objects.create(name="Test Project", description="Test project desc")

        # Create a forum post with project link
        post_data = {
            "title": "Test Post with Project",
            "category": self.category.id,
            "description": "Test Description with project link",
            "project": project.id,
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify post has project link
        post = ForumPost.objects.first()
        self.assertIsNotNone(post.project)
        self.assertEqual(post.project.id, project.id)

    def test_forum_post_with_organization_link(self):
        # Create a test organization
        organization = Organization.objects.create(name="Test Org", url="https://test.org")

        # Create a forum post with organization link
        post_data = {
            "title": "Test Post with Organization",
            "category": self.category.id,
            "description": "Test Description with organization link",
            "organization": organization.id,
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify post has organization link
        post = ForumPost.objects.first()
        self.assertIsNotNone(post.organization)
        self.assertEqual(post.organization.id, organization.id)

    def test_forum_post_with_all_links(self):
        # Create test entities
        organization = Organization.objects.create(name="Test Org", url="https://test.org")
        project = Project.objects.create(name="Test Project", description="Test project desc")
        repo = Repo.objects.create(
            name="Test Repo", description="Test repo desc", repo_url="https://github.com/test/repo"
        )

        # Create a forum post with all links
        post_data = {
            "title": "Test Post with All Links",
            "category": self.category.id,
            "description": "Test Description with all links",
            "repo": repo.id,
            "project": project.id,
            "organization": organization.id,
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify post has all links
        post = ForumPost.objects.first()
        self.assertIsNotNone(post.repo)
        self.assertIsNotNone(post.project)
        self.assertIsNotNone(post.organization)
        self.assertEqual(post.repo.id, repo.id)
        self.assertEqual(post.project.id, project.id)
        self.assertEqual(post.organization.id, organization.id)

    def test_forum_post_with_invalid_ids(self):
        # Test with invalid category ID (non-integer)
        post_data = {
            "title": "Test Post",
            "category": "invalid",
            "description": "Test Description",
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "Invalid category")

        # Test with invalid repo ID (non-integer)
        post_data = {
            "title": "Test Post",
            "category": self.category.id,
            "description": "Test Description",
            "repo": "not_a_number",
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "Invalid repo ID")

        # Test with non-existent repo ID
        post_data = {
            "title": "Test Post",
            "category": self.category.id,
            "description": "Test Description",
            "repo": 99999,
        }

        response = self.client.post(
            reverse("add_forum_post"), data=json.dumps(post_data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "Invalid repo ID")


class TopEarnersTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test users
        self.user1 = User.objects.create_user(username="earner1", password="testpass")
        self.user2 = User.objects.create_user(username="earner2", password="testpass")
        self.user3 = User.objects.create_user(username="earner3", password="testpass")

        # Create user profiles
        self.profile1 = UserProfile.objects.get(user=self.user1)
        self.profile2 = UserProfile.objects.get(user=self.user2)
        self.profile3 = UserProfile.objects.get(user=self.user3)

        # Create a test repository
        self.repo = Repo.objects.create(name="TestRepo", repo_url="https://github.com/test/repo")

    def _get_top_earners_queryset(self):
        """Helper method that executes the same query as in the home view"""
        from django.db.models import Case, Count, DecimalField, F, Q, Sum, Value, When
        from django.db.models.functions import Coalesce

        return (
            UserProfile.objects.annotate(
                github_earnings=Coalesce(
                    Sum("github_issues__p2p_amount_usd", filter=Q(github_issues__p2p_amount_usd__isnull=False)),
                    Value(0),
                    output_field=DecimalField(),
                ),
                has_github_issues=Count("github_issues", filter=Q(github_issues__p2p_amount_usd__isnull=False)),
                total_earnings=Case(
                    # If user has GitHub issues with payments, use those
                    When(has_github_issues__gt=0, then=F("github_earnings")),
                    # Otherwise fall back to the existing winnings field
                    default=Coalesce(F("winnings"), Value(0), output_field=DecimalField()),
                    output_field=DecimalField(),
                ),
            )
            .filter(total_earnings__gt=0)
            .select_related("user")
            .order_by("-total_earnings")[:5]
        )

    def test_top_earners_queryset_from_github_issues(self):
        """Test that top earners queryset calculation uses GitHub issue payments when available"""
        # Create GitHub issues with payments for user1
        GitHubIssue.objects.create(
            issue_id=1,
            title="Issue 1",
            state="closed",
            url="https://github.com/test/repo/issues/1",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile1,
            p2p_amount_usd=Decimal("50.00"),
        )
        GitHubIssue.objects.create(
            issue_id=2,
            title="Issue 2",
            state="closed",
            url="https://github.com/test/repo/issues/2",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile1,
            p2p_amount_usd=Decimal("30.00"),
        )

        # Set winnings for user2 (fallback case)
        self.profile2.winnings = Decimal("60.00")
        self.profile2.save()

        top_earners_list = list(self._get_top_earners_queryset())

        # Verify user1's total is calculated from GitHub issues (50 + 30 = 80)
        user1_earner = next((e for e in top_earners_list if e.user == self.user1), None)
        self.assertIsNotNone(user1_earner)
        self.assertEqual(user1_earner.total_earnings, Decimal("80.00"))

        # Verify user2's total comes from winnings field
        user2_earner = next((e for e in top_earners_list if e.user == self.user2), None)
        self.assertIsNotNone(user2_earner)
        self.assertEqual(user2_earner.total_earnings, Decimal("60.00"))

        # Verify correct ordering (user1 with 80 should be before user2 with 60)
        self.assertEqual(top_earners_list[0].user, self.user1)
        self.assertEqual(top_earners_list[1].user, self.user2)

    def test_top_earners_queryset_fallback_to_winnings(self):
        """Test that winnings field is used when no GitHub issues with payments exist"""
        # Set winnings for user profiles without GitHub issues
        self.profile1.winnings = Decimal("100.00")
        self.profile1.save()

        self.profile2.winnings = Decimal("50.00")
        self.profile2.save()

        top_earners_list = list(self._get_top_earners_queryset())

        # All earnings should come from winnings field
        user1_earner = next((e for e in top_earners_list if e.user == self.user1), None)
        self.assertIsNotNone(user1_earner)
        self.assertEqual(user1_earner.total_earnings, Decimal("100.00"))

        user2_earner = next((e for e in top_earners_list if e.user == self.user2), None)
        self.assertIsNotNone(user2_earner)
        self.assertEqual(user2_earner.total_earnings, Decimal("50.00"))

    def test_top_earners_queryset_mixed_sources(self):
        """Test that the calculation works correctly with mixed payment sources"""
        # User1: Has GitHub issues with payments
        GitHubIssue.objects.create(
            issue_id=10,
            title="Paid Issue",
            state="closed",
            url="https://github.com/test/repo/issues/10",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile1,
            p2p_amount_usd=Decimal("75.00"),
        )
        # Set winnings for user1 - should be ignored since GitHub issues exist
        self.profile1.winnings = Decimal("10.00")
        self.profile1.save()

        # User2: Only has winnings, no GitHub issues
        self.profile2.winnings = Decimal("50.00")
        self.profile2.save()

        # User3: Has GitHub issues but no payments (p2p_amount_usd is None)
        GitHubIssue.objects.create(
            issue_id=20,
            title="Unpaid Issue",
            state="open",
            url="https://github.com/test/repo/issues/20",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            repo=self.repo,
            user_profile=self.profile3,
            p2p_amount_usd=None,
        )
        self.profile3.winnings = Decimal("40.00")
        self.profile3.save()

        top_earners_list = list(self._get_top_earners_queryset())

        # User1 should use GitHub issue payment (75.00), not winnings (10.00)
        user1_earner = next((e for e in top_earners_list if e.user == self.user1), None)
        self.assertIsNotNone(user1_earner)
        self.assertEqual(user1_earner.total_earnings, Decimal("75.00"))

        # User2 should use winnings
        user2_earner = next((e for e in top_earners_list if e.user == self.user2), None)
        self.assertIsNotNone(user2_earner)
        self.assertEqual(user2_earner.total_earnings, Decimal("50.00"))

        # User3 should use winnings since GitHub issue has no payment
        user3_earner = next((e for e in top_earners_list if e.user == self.user3), None)
        self.assertIsNotNone(user3_earner)
        self.assertEqual(user3_earner.total_earnings, Decimal("40.00"))


class DarkModeTests(TestCase):
    """Test suite for dark mode functionality"""

    def setUp(self):
        self.client = Client()

    def test_set_theme_endpoint_accepts_dark(self):
        """Test that the set-theme endpoint accepts and saves dark theme"""
        response = self.client.post(
            reverse("set_theme"), data=json.dumps({"theme": "dark"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "dark")

    def test_set_theme_endpoint_accepts_light(self):
        """Test that the set-theme endpoint accepts and saves light theme"""
        response = self.client.post(
            reverse("set_theme"), data=json.dumps({"theme": "light"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["theme"], "light")

    def test_set_theme_invalid_method(self):
        """Test that GET request to set-theme endpoint returns error"""
        response = self.client.get(reverse("set_theme"))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")

    def test_dark_mode_toggle_in_base_template(self):
        """Test that dark mode toggle is present in base template"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check for dark mode JS and CSS references (may be hashed in production)
        self.assertTrue(
            "darkMode" in response.content.decode() or "dark-mode" in response.content.decode(),
            "Dark mode script reference not found in response",
        )
        self.assertContains(response, "custom-scrollbar")

    def test_dark_mode_script_loads(self):
        """Test that dark mode JS script is included in pages"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Check for dark mode related content (script tag with darkMode reference)
        content = response.content.decode()
        self.assertTrue("darkMode.js" in content or "darkMode" in content, "Dark mode script not found in response")


class StatusPageTests(TestCase):
    """Test suite for status page functionality"""

    def setUp(self):
        self.client = Client()

    def test_status_page_loads(self):
        """Test that the status page loads without errors"""
        response = self.client.get(reverse("status_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.context)

    def test_status_page_has_required_context(self):
        """Test that status page provides expected context data"""
        response = self.client.get(reverse("status_page"))
        self.assertEqual(response.status_code, 200)
        status = response.context["status"]

        # Check for essential status data keys
        self.assertIn("management_commands", status)
        self.assertIn("available_commands", status)
