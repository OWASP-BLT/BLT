from django.test import TestCase

from website.models import Organization, Project, Repo


class ParticipationStatsTestCase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.project = Project.objects.create(name="Test Project", organization=self.org)

    def test_get_participation_stats_empty(self):
        """Should return 52 zeros if no repos exist"""
        stats = self.project.get_participation_stats()
        self.assertEqual(len(stats), 52)
        self.assertEqual(stats, [0] * 52)

    def test_get_participation_stats_aggregation(self):
        """Should aggregate (sum) stats from multiple active repos"""
        repo1_stats = [i for i in range(52)]
        repo2_stats = [2 * i for i in range(52)]

        Repo.objects.create(
            project=self.project,
            name="repo1",
            repo_url="https://github.com/test/repo1",
            is_archived=False,
            participation_stats=repo1_stats,
        )
        Repo.objects.create(
            project=self.project,
            name="repo2",
            repo_url="https://github.com/test/repo2",
            is_archived=False,
            participation_stats=repo2_stats,
        )

        # This one is archived, should be ignored
        Repo.objects.create(
            project=self.project,
            name="repo3",
            repo_url="https://github.com/test/repo3",
            is_archived=True,
            participation_stats=[100] * 52,
        )

        expected_stats = [3 * i for i in range(52)]
        self.assertEqual(self.project.get_participation_stats(), expected_stats)

    def test_get_participation_stats_malformed(self):
        """Should ignore malformed/wrong-sized stats"""
        Repo.objects.create(
            project=self.project,
            name="malformed",
            repo_url="https://github.com/test/malformed",
            is_archived=False,
            participation_stats=[1, 2, 3],  # Not 52 entries
        )

        stats = self.project.get_participation_stats()
        self.assertEqual(stats, [0] * 52)

    def test_calculate_freshness_with_stats(self):
        """Should use participation stats for freshness calculation if available"""
        # Repo with activity in index 51 (last week)
        stats = [0] * 52
        stats[51] = 5
        Repo.objects.create(
            project=self.project,
            name="fresh_repo",
            repo_url="https://github.com/test/fresh",
            is_archived=False,
            participation_stats=stats,
        )

        # raw_score = 1.0 (very fresh)
        # freshness = (1.0 / 20) * 100 = 5.0
        self.assertEqual(self.project.calculate_freshness(), 5.0)

    def test_calculate_freshness_consistency_bonus(self):
        """Should apply consistency bonus if repo is active in 3+ weeks of last quarter"""
        stats = [0] * 52
        stats[51] = 1
        stats[50] = 1
        stats[49] = 1  # 3 active weeks in last 12 weeks (40-51)

        Repo.objects.create(
            project=self.project,
            name="consistent_repo",
            repo_url="https://github.com/test/consistent",
            is_archived=False,
            participation_stats=stats,
        )

        # raw_score = 1.0 (recent) + 0.1 (bonus) = 1.1
        # freshness = (1.1 / 20) * 100 = 5.5
        self.assertEqual(self.project.calculate_freshness(), 5.5)
