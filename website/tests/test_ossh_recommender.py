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
            ("python", 8),     # Medium-high weight
            ("api", 2),        # Low weight
        ]
        language_weights = {}  # No language weights for channels
        
        recommended = discussion_channel_recommender(user_tags, language_weights, top_n=5)
        
        # Channel3 should rank highest: security(10) + python(8) + django(0) = 18
        # Channel1 should rank second: security(10) + python(8) = 18
        # Channel2 should rank lowest: api(2) = 2
        
        self.assertTrue(len(recommended) >= 2)
        
        # Check that Channel1 or Channel3 is recommended first (both score 18)
        top_channel = recommended[0]["channel"]
        self.assertIn(top_channel.name, ["Security Experts", "Django Community"])
        
        # Check that Channel2 ranks lower (if it appears)
        if len(recommended) >= 3:
            last_channel = recommended[-1]["channel"]
            self.assertEqual(last_channel.name, "API Developers")

    def test_no_matching_tags(self):
        """Test behavior when user has no matching tags"""
        user_tags = [("react", 5), ("typescript", 3)]  # Tags not in any channel
        language_weights = {}
        
        recommended = discussion_channel_recommender(user_tags, language_weights)
        
        # Should return empty list or no recommendations
        self.assertEqual(len(recommended), 0)

    def test_scoring_uses_weights_not_counts(self):
        """Verify the bug is fixed: should use tag weights, not just count matches"""
        user_tags = [
            ("python", 100),  # Very high weight - only channel1 has this
            ("django", 1),    # Very low weight - only channel3 has this
        ]
        language_weights = {}
        
        recommended = discussion_channel_recommender(user_tags, language_weights, top_n=5)
        
        # Channel1 (security, python): score = 100
        # Channel3 (django, python, security): score = 100 + 1 = 101
        # Channel2 (api): score = 0 (no matches)
        
        self.assertTrue(len(recommended) >= 2)
        
        # Channel3 should rank first with 101
        self.assertEqual(recommended[0]["channel"].name, "Django Community")
        self.assertEqual(recommended[0]["relevance_score"], 101)
        
        # Channel1 should rank second with 100
        self.assertEqual(recommended[1]["channel"].name, "Security Experts")
        self.assertEqual(recommended[1]["relevance_score"], 100)