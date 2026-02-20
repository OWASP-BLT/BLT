#!/usr/bin/env python
"""
Consolidated test suite for duplicate bug checker.

IMPORTANT: The form has 3 fields:
  1. URL (name='url') - Domain URL
  2. Bug Title (name='description') - Short title
  3. Bug Description (name='markdown_description') - Detailed description

The duplicate checker uses: Title + Description combined for better matching

Usage:
  In Docker:  docker exec app python test_duplicate_checker.py quick
  With Django: python manage.py test
"""

import json
import os
import sys

from django.contrib.auth.models import User
from django.test import Client, TestCase

from website.duplicate_checker import (
    SequenceMatcherStrategy,
    check_for_duplicates,
)
from website.models import Domain, Issue


class DuplicateCheckerUnitTests(TestCase):
    """Unit tests for duplicate checker functions"""

    def setUp(self):
        self.strategy = SequenceMatcherStrategy()

    def test_normalize_text(self):
        """Test text normalization"""
        text = "This is a TEST with Special@Characters!"
        normalized = self.strategy.normalize_text(text)
        self.assertEqual(normalized, "this is a test with special characters")

    def test_extract_domain(self):
        """Test domain extraction from URLs"""
        test_cases = [
            ("https://www.example.com/page", "example.com"),
            ("http://subdomain.example.com", "subdomain.example.com"),
            ("https://example.com/path/to/page", "example.com"),
        ]
        for url, expected in test_cases:
            result = self.strategy.extract_domain_from_url(url)
            self.assertEqual(result, expected)

    def test_calculate_similarity(self):
        """Test similarity calculation"""
        text1 = "The login button is not working"
        text2 = "Login button doesn't work"
        text3 = "The payment gateway has an error"

        sim1 = self.strategy.calculate_similarity(text1, text2)
        sim2 = self.strategy.calculate_similarity(text1, text3)

        self.assertGreater(sim1, sim2, "Similar texts should have higher similarity")
        self.assertGreater(sim1, 0.5)

    def test_extract_keywords(self):
        """Test keyword extraction"""
        text = "The login button is not working properly on the homepage"
        keywords = self.strategy.extract_keywords(text)

        self.assertIn("login", keywords)
        self.assertIn("button", keywords)
        self.assertNotIn("the", keywords)  # stop word
        self.assertNotIn("is", keywords)  # stop word


class DuplicateCheckerIntegrationTests(TestCase):
    """Integration tests with database"""

    def setUp(self):
        """Set up test data"""
        import secrets

        self.user = User.objects.create_user(username="testuser", password=secrets.token_urlsafe(32))
        self.domain = Domain.objects.create(name="example.com", url="https://example.com")
        self.issue1 = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url="https://example.com/login",
            description="Login button not working",
            label=2,  # Functional bug
        )

    def test_find_exact_duplicate(self):
        """Test finding exact duplicate"""
        result = check_for_duplicates("https://example.com/login", "Login button not working", self.domain)

        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["confidence"], "high")
        self.assertGreater(len(result["similar_bugs"]), 0)

    def test_find_similar_bug(self):
        """Test finding similar but not exact bug"""
        result = check_for_duplicates("https://example.com/login", "The login form is broken", self.domain)

        # Should find the similar bug
        self.assertGreater(len(result["similar_bugs"]), 0)
        # Verify the confidence level is appropriate for similar (not exact) matches
        self.assertIn(result["confidence"], ["high", "medium", "low"])

    def test_no_duplicate_different_domain(self):
        """Test that different domain doesn't match"""
        other_domain = Domain.objects.create(name="other.com", url="https://other.com")

        result = check_for_duplicates("https://other.com/login", "Login button not working", other_domain)

        # Should not find bugs from different domain
        self.assertEqual(len(result["similar_bugs"]), 0)


class DuplicateCheckerAPITests(TestCase):
    """API endpoint tests"""

    def setUp(self):
        """Set up test client and data"""
        import secrets

        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password=secrets.token_urlsafe(32))
        self.domain = Domain.objects.create(name="example.com", url="https://example.com")
        self.issue = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url="https://example.com/test",
            description="Test bug description",
            label=2,
        )

    def test_check_duplicate_api(self):
        """Test the check duplicate API endpoint"""
        response = self.client.post(
            "/api/v1/bugs/check-duplicate/",
            data=json.dumps({"url": "https://example.com/test", "description": "Test bug description"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("is_duplicate", data)
        self.assertIn("confidence", data)
        self.assertIn("similar_bugs", data)
        # Verify semantic correctness for exact match
        self.assertTrue(data["is_duplicate"])
        self.assertEqual(data["confidence"], "high")
        self.assertGreater(len(data["similar_bugs"]), 0)

    def test_find_similar_api(self):
        """Test the find similar bugs API endpoint"""
        response = self.client.get(
            "/api/v1/bugs/find-similar/",
            {"url": "https://example.com/test", "description": "Test bug", "threshold": "0.5"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)


def run_quick_tests():
    """Run quick tests for verification"""
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.write("Quick Duplicate Checker Tests\n")
    sys.stdout.write("=" * 60 + "\n")

    passed = 0
    failed = 0

    # Initialize strategy
    from website.duplicate_checker import SequenceMatcherStrategy

    strategy = SequenceMatcherStrategy()

    # Test 1: Text normalization
    sys.stdout.write("\n1. Testing text normalization...\n")
    try:
        text = "This is a TEST!"
        normalized = strategy.normalize_text(text)
        sys.stdout.write(f"   Input: '{text}'\n")
        sys.stdout.write(f"   Output: '{normalized}'\n")
        assert normalized == "this is a test"
        sys.stdout.write("   ✓ Passed\n")
        passed += 1
    except Exception as e:
        sys.stdout.write(f"   ✗ Failed: {e}\n")
        failed += 1

    # Test 2: Domain extraction
    sys.stdout.write("\n2. Testing domain extraction...\n")
    try:
        url = "https://www.example.com/page"
        domain = strategy.extract_domain_from_url(url)
        sys.stdout.write(f"   URL: {url}\n")
        sys.stdout.write(f"   Domain: {domain}\n")
        assert domain == "example.com"
        sys.stdout.write("   ✓ Passed\n")
        passed += 1
    except Exception as e:
        sys.stdout.write(f"   ✗ Failed: {e}\n")
        failed += 1

    # Test 3: Similarity
    sys.stdout.write("\n3. Testing similarity calculation...\n")
    try:
        text1 = "Login button not working"
        text2 = "Login button doesn't work"
        similarity = strategy.calculate_similarity(text1, text2)
        sys.stdout.write(f"   Text 1: '{text1}'\n")
        sys.stdout.write(f"   Text 2: '{text2}'\n")
        sys.stdout.write(f"   Similarity: {similarity:.2f}\n")
        assert similarity > 0.5
        sys.stdout.write("   ✓ Passed\n")
        passed += 1
    except Exception as e:
        sys.stdout.write(f"   ✗ Failed: {e}\n")
        failed += 1

    # Test 4: Database integration
    sys.stdout.write("\n4. Testing database integration...\n")
    try:
        # Check if we can query the database
        issue_count = Issue.objects.count()
        domain_count = Domain.objects.count()
        sys.stdout.write(f"   Issues in DB: {issue_count}\n")
        sys.stdout.write(f"   Domains in DB: {domain_count}\n")
        sys.stdout.write("   ✓ Passed\n")
        passed += 1
    except Exception as e:
        sys.stdout.write(f"   ✗ Failed: {e}\n")
        failed += 1

    # Test 5: Check for duplicates function
    sys.stdout.write("\n5. Testing check_for_duplicates function...\n")
    try:
        result = check_for_duplicates("https://example.com/test", "Test bug description", threshold=0.6)
        assert "is_duplicate" in result
        assert "confidence" in result
        assert "similar_bugs" in result
        sys.stdout.write(f"   Result: {result['confidence']} confidence\n")
        sys.stdout.write(f"   Similar bugs found: {len(result['similar_bugs'])}\n")
        sys.stdout.write("   ✓ Passed\n")
        passed += 1
    except Exception as e:
        sys.stdout.write(f"   ✗ Failed: {e}\n")
        failed += 1

    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write(f"Results: {passed} passed, {failed} failed\n")
    sys.stdout.write("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    # Setup Django when script is run directly
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
    django.setup()

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        success = run_quick_tests()
        sys.exit(0 if success else 1)
    else:
        sys.stdout.write("Duplicate Checker Test Suite\n")
        sys.stdout.write("\nUsage:\n")
        sys.stdout.write("  Quick test:  python test_duplicate_checker.py quick\n")
        sys.stdout.write("  Django test: python manage.py test\n")
        sys.stdout.write("  In Docker:   docker exec app python test_duplicate_checker.py quick\n")
