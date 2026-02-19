"""
Enhanced test coverage for OSSH repository links feature (Issue #86).

Provides comprehensive testing for:
- Repository link validation and display
- URL handling and edge cases
- Project relationship link display
"""

from django.test import TestCase, Client
from website.models import Repo, Tag, Project
from website.views.ossh import repo_recommender


class RepositoryLinksEnhancementTests(TestCase):
    """Test suite for enhanced repository links functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create tags
        self.tag_python = Tag.objects.create(name="python")
        self.tag_django = Tag.objects.create(name="django")

        # Create project
        self.project = Project.objects.create(
            name="Test Project",
            slug="test-project",
            url="https://example.com/projects/test",
        )

        # Create repository with all URL fields
        self.repo_complete = Repo.objects.create(
            name="Complete Repo",
            repo_url="https://github.com/test/complete-repo",
            homepage_url="https://complete-repo.example.com",
            description="A repository with all fields",
            primary_language="Python",
            stars=100,
            forks=50,
            project=self.project,
        )
        self.repo_complete.tags.add(self.tag_python, self.tag_django)

        # Create repository with missing homepage
        self.repo_partial = Repo.objects.create(
            name="Partial Repo",
            repo_url="https://github.com/test/partial-repo",
            homepage_url="",
            description="Repository missing homepage",
            primary_language="Python",
            stars=50,
            forks=25,
        )
        self.repo_partial.tags.add(self.tag_python)

        # Create repository with no project
        self.repo_no_project = Repo.objects.create(
            name="No Project Repo",
            repo_url="https://github.com/test/no-project",
            description="Repository with no project",
            primary_language="JavaScript",
            stars=30,
            forks=10,
            project=None,
        )

    def test_repo_recommender_includes_project_data(self):
        """Test that recommender properly loads project relationships"""
        user_tags = [("python", 10), ("django", 5)]
        language_weights = {"Python": 8}

        recommended = repo_recommender(user_tags, language_weights)

        complete_result = next(
            (item for item in recommended if item["repo"].id == self.repo_complete.id),
            None,
        )

        self.assertIsNotNone(complete_result)
        self.assertEqual(complete_result["repo"].project.name, "Test Project")

    def test_repo_recommender_handles_missing_homepage(self):
        """Test recommender handles empty homepage URLs gracefully"""
        user_tags = [("python", 10)]
        language_weights = {"Python": 5}

        recommended = repo_recommender(user_tags, language_weights)

        has_partial = any(
            item["repo"].id == self.repo_partial.id for item in recommended
        )
        self.assertTrue(has_partial)

    def test_repo_recommender_handles_null_project(self):
        """Test recommender handles repos without project relationship"""
        user_tags = [("javascript", 8)]
        language_weights = {"JavaScript": 4}

        recommended = repo_recommender(user_tags, language_weights)
        self.assertIsInstance(recommended, list)

    def test_all_repos_have_required_url(self):
        """Test that all recommended repos have valid repo_url"""
        user_tags = [("python", 10)]
        language_weights = {"Python": 5}

        recommended = repo_recommender(user_tags, language_weights)

        for item in recommended:
            self.assertIsNotNone(item["repo"].repo_url)
            self.assertNotEqual(item["repo"].repo_url, "")
            self.assertTrue(item["repo"].repo_url.startswith("http"))

    def test_relevance_scoring_accuracy(self):
        """Test relevance scoring with multiple matching tags"""
        user_tags = [("python", 10), ("django", 8)]
        language_weights = {"Python": 12}

        recommended = repo_recommender(user_tags, language_weights)

        complete_result = next(
            (item for item in recommended if item["repo"].id == self.repo_complete.id),
            None,
        )

        self.assertIsNotNone(complete_result)
        # Score = python(10) + django(8) + Python(12) = 30
        self.assertEqual(complete_result["relevance_score"], 30)

    def test_results_sorted_by_relevance(self):
        """Test results are properly sorted by relevance score"""
        # repo_high matches both tags = higher score
        repo_high = Repo.objects.create(
            name="High Score Repo",
            repo_url="https://github.com/test/high-score",
            description="High relevance repository",
            primary_language="Python",
            stars=10,
        )
        repo_high.tags.add(self.tag_python, self.tag_django)

        # repo_low matches only one tag = lower score
        repo_low = Repo.objects.create(
            name="Low Score Repo",
            repo_url="https://github.com/test/low-score",
            description="Low relevance repository",
            primary_language="JavaScript",
            stars=10,
        )
        repo_low.tags.add(self.tag_python)

        user_tags = [("python", 10), ("django", 8)]
        language_weights = {"Python": 5}

        recommended = repo_recommender(user_tags, language_weights)

        # Verify descending order
        for i in range(len(recommended) - 1):
            self.assertGreaterEqual(
                recommended[i]["relevance_score"],
                recommended[i + 1]["relevance_score"],
            )

    def test_reasoning_provides_clear_explanation(self):
        """Test reasoning field explains match criteria"""
        user_tags = [("python", 10)]
        language_weights = {"Python": 5}

        recommended = repo_recommender(user_tags, language_weights)

        for item in recommended:
            self.assertIsNotNone(item["reasoning"])
            self.assertNotEqual(item["reasoning"], "")
            reasoning_lower = item["reasoning"].lower()
            self.assertTrue(
                "matching tags" in reasoning_lower
                or "matching language" in reasoning_lower
            )


class RepositoryLinksEdgeCasesTests(TestCase):
    """Test edge cases and error handling"""

    def test_empty_user_tags_returns_empty(self):
        """Test recommender with no user tags"""
        recommended = repo_recommender([], {})
        self.assertEqual(len(recommended), 0)

    def test_no_matching_repos_returns_empty(self):
        """Test when no repos match criteria"""
        tag = Tag.objects.create(name="rust")
        repo = Repo.objects.create(
            name="Rust Repo",
            repo_url="https://github.com/test/rust-repo",
            description="Rust project",
            primary_language="Rust",
        )
        repo.tags.add(tag)

        user_tags = [("cobol", 10)]
        language_weights = {"Assembly": 8}

        recommended = repo_recommender(user_tags, language_weights)
        self.assertEqual(len(recommended), 0)

    def test_max_results_limit(self):
        """Test that recommender limits results to exactly 5"""
        tag = Tag.objects.create(name="test")
        for i in range(10):
            repo = Repo.objects.create(
                name=f"Repo {i}",
                repo_url=f"https://github.com/test/repo-{i}",
                description="Test",
                primary_language="Python",
            )
            repo.tags.add(tag)

        user_tags = [("test", 10)]
        language_weights = {"Python": 5}

        recommended = repo_recommender(user_tags, language_weights)
        self.assertEqual(len(recommended), 5)
