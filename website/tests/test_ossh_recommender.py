from django.test import TestCase

from website.models import OsshDiscussionChannel, Tag
from website.views.ossh import discussion_channel_recommender


class DiscussionChannelRecommenderTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create tags
        self.tag_security = Tag.objects.create(name="security")
        self.tag_api = Tag.objects.create(name="api")
        self.tag_python = Tag.objects.create(name="python")
        self.tag_django = Tag.objects.create(name="django")

        # Create channels
        self.channel1 = OsshDiscussionChannel.objects.create(
            name="Security Experts",
            source="Discord",
            external_id="test_123",
        )
        self.channel1.tags.add(self.tag_security, self.tag_python)

        self.channel2 = OsshDiscussionChannel.objects.create(
            name="API Developers",
            source="Discord",
            external_id="test_456",
        )
        self.channel2.tags.add(self.tag_api)

        self.channel3 = OsshDiscussionChannel.objects.create(
            name="Django Community",
            source="Slack",
            external_id="test_789",
        )
        self.channel3.tags.add(self.tag_django, self.tag_python, self.tag_security)

    def test_weighted_scoring(self):
        """Test that channels are scored based on tag weights, not just counts"""
        # User has high weight for 'security' and 'python', low for 'api'
        user_tags = [
            ("security", 10),  # High weight
            ("python", 8),  # Medium-high weight
            ("api", 2),  # Low weight
        ]
        language_weights = {}  # Language weights are ignored for channels

        recommended = discussion_channel_recommender(user_tags, language_weights, top_n=5)

        # Channel3: security(10) + python(8) = 18 (django tag has no user weight)
        # Channel1: security(10) + python(8) = 18
        # Channel2: api(2) = 2

        self.assertTrue(len(recommended) >= 2)

        # Check that Channel1 or Channel3 is recommended first (both score 18)
        top_channel = recommended[0]["channel"]
        self.assertIn(top_channel.name, ["Security Experts", "Django Community"])
        self.assertEqual(recommended[0]["relevance_score"], 18)

        # Check that Channel2 ranks lower (if it appears)
        if len(recommended) >= 3:
            last_channel = recommended[-1]["channel"]
            self.assertEqual(last_channel.name, "API Developers")
            self.assertEqual(recommended[-1]["relevance_score"], 2)

    def test_no_matching_tags(self):
        """Test behavior when user has no matching tags"""
        user_tags = [("react", 5), ("typescript", 3)]  # Tags not in any channel
        language_weights = {}

        recommended = discussion_channel_recommender(user_tags, language_weights)

        # Should return empty list when no tags match
        self.assertEqual(len(recommended), 0)

    def test_scoring_uses_weights_not_counts(self):
        """Verify the bug fix: should use tag weights, not just count matches"""
        user_tags = [
            ("python", 100),  # Very high weight
            ("django", 1),  # Very low weight
        ]
        language_weights = {}

        recommended = discussion_channel_recommender(user_tags, language_weights, top_n=5)

        # Channel1 (security, python): score = 100 (only python matches)
        # Channel3 (django, python, security): score = 100 + 1 = 101
        # Channel2 (api): score = 0 (no matches)

        self.assertGreaterEqual(len(recommended), 2)

        # Channel3 should rank first with 101
        self.assertEqual(recommended[0]["channel"].name, "Django Community")
        self.assertEqual(recommended[0]["relevance_score"], 101)

        # Channel1 should rank second with 100
        self.assertEqual(recommended[1]["channel"].name, "Security Experts")
        self.assertEqual(recommended[1]["relevance_score"], 100)

    def test_language_weights_are_ignored(self):
        """Test that language_weights parameter has no effect on channel scoring"""
        user_tags = [("security", 10), ("python", 5)]

        # Try with empty language weights
        recommended_no_lang = discussion_channel_recommender(user_tags, language_weights={}, top_n=5)

        # Try with populated language weights (should be ignored)
        recommended_with_lang = discussion_channel_recommender(
            user_tags, language_weights={"Python": 100, "JavaScript": 50}, top_n=5
        )

        # Both should produce identical results since channels don't have language metadata
        self.assertEqual(len(recommended_no_lang), len(recommended_with_lang))

        for i, rec in enumerate(recommended_no_lang):
            self.assertEqual(rec["channel"].id, recommended_with_lang[i]["channel"].id)
            self.assertEqual(rec["relevance_score"], recommended_with_lang[i]["relevance_score"])

    def test_reasoning_only_includes_tags(self):
        """Test that reasoning string only mentions matching tags, not languages"""
        user_tags = [("security", 10), ("python", 5)]
        language_weights = {}

        recommended = discussion_channel_recommender(user_tags, language_weights, top_n=1)

        self.assertGreater(len(recommended), 0)

        reasoning = recommended[0]["reasoning"]

        # Should contain "Matching tags:"
        self.assertIn("Matching tags:", reasoning)

        # Should NOT contain "Matching language:" (removed after Issue 2 fix)
        self.assertNotIn("Matching language:", reasoning)

    def test_top_n_limit(self):
        """Test that top_n parameter correctly limits results"""
        user_tags = [
            ("security", 10),
            ("python", 8),
            ("api", 5),
            ("django", 3),
        ]
        language_weights = {}

        # Request only top 2
        recommended = discussion_channel_recommender(user_tags, language_weights, top_n=2)

        self.assertEqual(len(recommended), 2)

        # Verify they're sorted by relevance_score descending
        self.assertGreaterEqual(recommended[0]["relevance_score"], recommended[1]["relevance_score"])

    def test_zero_score_channels_excluded(self):
        """Test that channels with zero relevance score are not returned"""
        # Only provide tags that don't match any channel
        user_tags = [("rust", 10), ("golang", 5)]
        language_weights = {}

        recommended = discussion_channel_recommender(user_tags, language_weights)

        # No channels should be returned
        self.assertEqual(len(recommended), 0)

    def test_partial_tag_match(self):
        """Test scoring when only some of channel's tags match user tags"""
        user_tags = [
            ("security", 20),  # Matches channel1 and channel3
            # Don't include 'python' tag
        ]
        language_weights = {}

        recommended = discussion_channel_recommender(user_tags, language_weights)

        # Both channel1 and channel3 have 'security' tag
        self.assertGreaterEqual(len(recommended), 2)

        # Both should have same score (20) since only 'security' matches
        for rec in recommended[:2]:  # Check first 2
            if rec["channel"].name in ["Security Experts", "Django Community"]:
                self.assertEqual(rec["relevance_score"], 20)
