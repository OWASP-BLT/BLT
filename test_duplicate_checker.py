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
import os
import sys

import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blt.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client, TestCase

from website.duplicate_checker import (
    calculate_similarity,
    check_for_duplicates,
    extract_domain_from_url,
    extract_keywords,
    normalize_text,
)
from website.models import Domain, Issue


class DuplicateCheckerUnitTests(TestCase):
    """Unit tests for duplicate checker functions"""
    
    def test_normalize_text(self):
        """Test text normalization"""
        text = "This is a TEST with Special@Characters!"
        normalized = normalize_text(text)
        self.assertEqual(normalized, "this is a test with special characters")
    
    def test_extract_domain(self):
        """Test domain extraction from URLs"""
        test_cases = [
            ("https://www.example.com/page", "example.com"),
            ("http://subdomain.example.com", "subdomain.example.com"),
            ("https://example.com/path/to/page", "example.com"),
        ]
        for url, expected in test_cases:
            result = extract_domain_from_url(url)
            self.assertEqual(result, expected)
    
    def test_calculate_similarity(self):
        """Test similarity calculation"""
        text1 = "The login button is not working"
        text2 = "Login button doesn't work"
        text3 = "The payment gateway has an error"
        
        sim1 = calculate_similarity(text1, text2)
        sim2 = calculate_similarity(text1, text3)
        
        self.assertGreater(sim1, sim2, "Similar texts should have higher similarity")
        self.assertGreater(sim1, 0.5)
    
    def test_extract_keywords(self):
        """Test keyword extraction"""
        text = "The login button is not working properly on the homepage"
        keywords = extract_keywords(text)
        
        self.assertIn("login", keywords)
        self.assertIn("button", keywords)
        self.assertNotIn("the", keywords)  # stop word
        self.assertNotIn("is", keywords)   # stop word


class DuplicateCheckerIntegrationTests(TestCase):
    """Integration tests with database"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.domain = Domain.objects.create(
            name='example.com',
            url='https://example.com'
        )
        self.issue1 = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url='https://example.com/login',
            description='Login button not working',
            label=2
        )
    
    def test_find_exact_duplicate(self):
        """Test finding exact duplicate"""
        result = check_for_duplicates(
            'https://example.com/login',
            'Login button not working',
            self.domain
        )
        
        self.assertTrue(result['is_duplicate'])
        self.assertEqual(result['confidence'], 'high')
        self.assertGreater(len(result['similar_bugs']), 0)
    
    def test_find_similar_bug(self):
        """Test finding similar but not exact bug"""
        result = check_for_duplicates(
            'https://example.com/login',
            'The login form is broken',
            self.domain
        )
        
        # Should find the similar bug
        self.assertGreater(len(result['similar_bugs']), 0)
    
    def test_no_duplicate_different_domain(self):
        """Test that different domain doesn't match"""
        other_domain = Domain.objects.create(
            name='other.com',
            url='https://other.com'
        )
        
        result = check_for_duplicates(
            'https://other.com/login',
            'Login button not working',
            other_domain
        )
        
        # Should not find bugs from different domain
        self.assertEqual(len(result['similar_bugs']), 0)


class DuplicateCheckerAPITests(TestCase):
    """API endpoint tests"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.domain = Domain.objects.create(
            name='example.com',
            url='https://example.com'
        )
        self.issue = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url='https://example.com/test',
            description='Test bug description',
            label=2
        )
    
    def test_check_duplicate_api(self):
        """Test the check duplicate API endpoint"""
        response = self.client.post(
            '/api/v1/bugs/check-duplicate/',
            data={
                'url': 'https://example.com/test',
                'description': 'Test bug description'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('is_duplicate', data)
        self.assertIn('confidence', data)
        self.assertIn('similar_bugs', data)
    
    def test_find_similar_api(self):
        """Test the find similar bugs API endpoint"""
        response = self.client.get(
            '/api/v1/bugs/find-similar/',
            {
                'url': 'https://example.com/test',
                'description': 'Test bug',
                'threshold': '0.5'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)


def run_quick_tests():
    """Run quick tests for verification"""
    print("=" * 60)
    print("Quick Duplicate Checker Tests")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test 1: Text normalization
    print("\n1. Testing text normalization...")
    try:
        text = "This is a TEST!"
        normalized = normalize_text(text)
        print(f"   Input: '{text}'")
        print(f"   Output: '{normalized}'")
        assert normalized == "this is a test"
        print("   ✓ Passed")
        passed += 1
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        failed += 1
    
    # Test 2: Domain extraction
    print("\n2. Testing domain extraction...")
    try:
        url = "https://www.example.com/page"
        domain = extract_domain_from_url(url)
        print(f"   URL: {url}")
        print(f"   Domain: {domain}")
        assert domain == "example.com"
        print("   ✓ Passed")
        passed += 1
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        failed += 1
    
    # Test 3: Similarity
    print("\n3. Testing similarity calculation...")
    try:
        text1 = "Login button not working"
        text2 = "Login button doesn't work"
        similarity = calculate_similarity(text1, text2)
        print(f"   Text 1: '{text1}'")
        print(f"   Text 2: '{text2}'")
        print(f"   Similarity: {similarity:.2f}")
        assert similarity > 0.5
        print("   ✓ Passed")
        passed += 1
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        failed += 1
    
    # Test 4: Database integration
    print("\n4. Testing database integration...")
    try:
        # Check if we can query the database
        issue_count = Issue.objects.count()
        domain_count = Domain.objects.count()
        print(f"   Issues in DB: {issue_count}")
        print(f"   Domains in DB: {domain_count}")
        print("   ✓ Passed")
        passed += 1
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        failed += 1
    
    # Test 5: Check for duplicates function
    print("\n5. Testing check_for_duplicates function...")
    try:
        result = check_for_duplicates(
            "https://example.com/test",
            "Test bug description",
            threshold=0.6
        )
        assert 'is_duplicate' in result
        assert 'confidence' in result
        assert 'similar_bugs' in result
        print(f"   Result: {result['confidence']} confidence")
        print(f"   Similar bugs found: {len(result['similar_bugs'])}")
        print("   ✓ Passed")
        passed += 1
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        success = run_quick_tests()
        sys.exit(0 if success else 1)
    else:
        print("Duplicate Checker Test Suite")
        print("\nUsage:")
        print("  Quick test:  python test_duplicate_checker.py quick")
        print("  Django test: python manage.py test")
        print("  In Docker:   docker exec app python test_duplicate_checker.py quick")
