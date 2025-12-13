"""
Tests for trademark search functionality.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Trademark, TrademarkOwner


class TrademarkModelTest(TestCase):
    """Test Trademark model."""

    def setUp(self):
        """Set up test data."""
        self.owner = TrademarkOwner.objects.create(
            name="Test Company Inc.",
            address1="123 Test St",
            city="Test City",
            state="CA",
            country="US",
            postcode="12345",
        )

        self.trademark = Trademark.objects.create(
            keyword="TEST_MARK",
            registration_number="1234567",
            serial_number="87654321",
            status_label="Live/Registered",
            description="Test trademark description",
        )
        self.trademark.owners.add(self.owner)

    def test_trademark_creation(self):
        """Test that trademarks are created properly."""
        self.assertEqual(Trademark.objects.count(), 1)
        self.assertEqual(self.trademark.keyword, "TEST_MARK")
        self.assertEqual(self.trademark.registration_number, "1234567")

    def test_trademark_owner_relationship(self):
        """Test the many-to-many relationship between trademarks and owners."""
        self.assertEqual(self.trademark.owners.count(), 1)
        self.assertEqual(self.trademark.owners.first(), self.owner)

    def test_trademark_str(self):
        """Test the string representation of Trademark."""
        self.assertEqual(str(self.trademark), "TEST_MARK")

    def test_trademark_owner_str(self):
        """Test the string representation of TrademarkOwner."""
        self.assertEqual(str(self.owner), "Test Company Inc.")


class TrademarkSearchViewTest(TestCase):
    """Test trademark search views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")

        # Create test trademarks
        self.owner = TrademarkOwner.objects.create(
            name="Apple Inc.",
            address1="One Apple Park Way",
            city="Cupertino",
            state="CA",
            country="US",
        )

        self.trademark1 = Trademark.objects.create(
            keyword="APPLE",
            registration_number="1234567",
            serial_number="87654321",
            status_label="Live/Registered",
            description="Computer hardware and software",
        )
        self.trademark1.owners.add(self.owner)

        self.trademark2 = Trademark.objects.create(
            keyword="GOOGLE",
            registration_number="2345678",
            serial_number="87654322",
            status_label="Live/Registered",
            description="Search engine services",
        )

    def test_trademark_search_page_loads(self):
        """Test that the trademark search page loads successfully."""
        response = self.client.get(reverse("trademark_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trademark Search")

    def test_trademark_detailview_with_keyword(self):
        """Test trademark detail view with keyword search."""
        response = self.client.get(reverse("trademark_detailview", kwargs={"slug": "APPLE"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APPLE")
        self.assertContains(response, "Computer hardware and software")

    def test_trademark_detailview_with_serial_number(self):
        """Test trademark detail view with serial number search."""
        response = self.client.get(reverse("trademark_detailview", kwargs={"slug": "87654321"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APPLE")

    def test_trademark_detailview_with_registration_number(self):
        """Test trademark detail view with registration number search."""
        response = self.client.get(reverse("trademark_detailview", kwargs={"slug": "1234567"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APPLE")

    def test_trademark_search_case_insensitive(self):
        """Test that trademark search is case-insensitive."""
        response = self.client.get(reverse("trademark_detailview", kwargs={"slug": "apple"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APPLE")

    def test_trademark_search_no_results(self):
        """Test trademark search with no matching results."""
        response = self.client.get(reverse("trademark_detailview", kwargs={"slug": "NONEXISTENT"}))
        self.assertEqual(response.status_code, 200)
        # Should show either error message or fallback to API

    def test_trademark_search_pagination(self):
        """Test that pagination works with local database results."""
        # Create 60 trademarks to test pagination (50 per page)
        for i in range(60):
            Trademark.objects.create(
                keyword=f"TEST_{i}",
                registration_number=f"REG{i}",
                serial_number=f"SER{i}",
                status_label="Live/Registered",
            )

        response = self.client.get(reverse("trademark_detailview", kwargs={"slug": "TEST"}))
        self.assertEqual(response.status_code, 200)
        # Check for pagination controls
        self.assertContains(response, "Page")

    def test_trademark_search_post_redirect(self):
        """Test that POST to trademark_search redirects to detail view."""
        response = self.client.post(reverse("trademark_search"), {"query": "APPLE"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/trademarks/query=APPLE", response.url)


class TrademarkIndexTest(TestCase):
    """Test that database indexes are properly created."""

    def test_keyword_index_exists(self):
        """Test that keyword field has an index."""
        # Get the field from the model
        field = Trademark._meta.get_field("keyword")
        self.assertTrue(field.db_index)

    def test_registration_number_index_exists(self):
        """Test that registration_number field has an index."""
        field = Trademark._meta.get_field("registration_number")
        self.assertTrue(field.db_index)

    def test_serial_number_index_exists(self):
        """Test that serial_number field has an index."""
        field = Trademark._meta.get_field("serial_number")
        self.assertTrue(field.db_index)

    def test_meta_indexes_defined(self):
        """Test that Meta indexes are defined."""
        indexes = Trademark._meta.indexes
        self.assertGreater(len(indexes), 0)
