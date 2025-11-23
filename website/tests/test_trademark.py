from datetime import date

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Organization, Trademark, TrademarkOwner


class TrademarkModelTests(TestCase):
    def setUp(self):
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            description="Test Description",
            slug="test-org",
        )

        # Create test trademark owners
        self.owner1 = TrademarkOwner.objects.create(
            name="Test Owner 1",
            address1="123 Test St",
            city="Test City",
            state="TS",
            country="USA",
            postcode="12345",
        )

        # Create test trademarks
        self.trademark1 = Trademark.objects.create(
            keyword="TEST MARK",
            registration_number="1234567",
            serial_number="87654321",
            status_label="Live/Registered",
            status_code="REG",
            filing_date=date(2020, 1, 1),
            registration_date=date(2021, 1, 1),
            description="Test trademark description",
            organization=self.organization,
        )
        self.trademark1.owners.add(self.owner1)

        self.trademark2 = Trademark.objects.create(
            keyword="ANOTHER MARK",
            registration_number="2345678",
            serial_number="98765432",
            status_label="Live/Pending",
            status_code="PEN",
            filing_date=date(2022, 1, 1),
            description="Another test trademark",
        )

    def test_trademark_creation(self):
        """Test that a trademark can be created"""
        self.assertEqual(self.trademark1.keyword, "TEST MARK")
        self.assertEqual(self.trademark1.registration_number, "1234567")
        self.assertEqual(self.trademark1.serial_number, "87654321")

    def test_trademark_string_representation(self):
        """Test the string representation of a trademark"""
        self.assertEqual(str(self.trademark1), "TEST MARK")

    def test_trademark_owner_relationship(self):
        """Test the many-to-many relationship between trademarks and owners"""
        self.assertIn(self.owner1, self.trademark1.owners.all())
        self.assertIn(self.trademark1, self.owner1.trademarks.all())

    def test_trademark_ordering(self):
        """Test that trademarks are ordered by filing_date descending"""
        trademarks = Trademark.objects.all()
        self.assertEqual(trademarks[0], self.trademark2)  # More recent filing date
        self.assertEqual(trademarks[1], self.trademark1)


class TrademarkLocalSearchViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create test trademarks
        self.trademark1 = Trademark.objects.create(
            keyword="DJANGO",
            registration_number="1111111",
            serial_number="11111111",
            status_label="Live/Registered",
            filing_date=date(2020, 1, 1),
            description="Python web framework",
        )

        self.trademark2 = Trademark.objects.create(
            keyword="PYTHON",
            registration_number="2222222",
            serial_number="22222222",
            status_label="Live/Registered",
            filing_date=date(2021, 1, 1),
            description="Programming language",
        )

        self.trademark3 = Trademark.objects.create(
            keyword="REACT",
            registration_number="3333333",
            serial_number="33333333",
            status_label="Live/Pending",
            filing_date=date(2022, 1, 1),
            description="JavaScript framework",
        )

    def test_local_search_view_loads(self):
        """Test that the local search view loads correctly"""
        response = self.client.get(reverse("trademark_local_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trademark Database Search")

    def test_local_search_by_keyword(self):
        """Test searching by keyword"""
        response = self.client.get(reverse("trademark_local_search"), {"q": "DJANGO"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DJANGO")
        self.assertNotContains(response, "PYTHON")
        self.assertNotContains(response, "REACT")

    def test_local_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        response = self.client.get(reverse("trademark_local_search"), {"q": "django"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DJANGO")

    def test_local_search_by_registration_number(self):
        """Test searching by registration number"""
        response = self.client.get(reverse("trademark_local_search"), {"q": "2222222"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PYTHON")
        self.assertContains(response, "2222222")

    def test_local_search_by_serial_number(self):
        """Test searching by serial number"""
        response = self.client.get(reverse("trademark_local_search"), {"q": "33333333"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REACT")
        self.assertContains(response, "33333333")

    def test_local_search_by_description(self):
        """Test searching by description"""
        response = self.client.get(reverse("trademark_local_search"), {"q": "framework"})
        self.assertEqual(response.status_code, 200)
        # Should find both DJANGO and REACT as they both have "framework" in description
        self.assertContains(response, "DJANGO")
        self.assertContains(response, "REACT")

    def test_local_search_no_results(self):
        """Test search with no results"""
        response = self.client.get(reverse("trademark_local_search"), {"q": "NONEXISTENT"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Results Found")

    def test_local_search_empty_query(self):
        """Test search with empty query"""
        response = self.client.get(reverse("trademark_local_search"), {"q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Search Local Trademark Database")

    def test_local_search_pagination(self):
        """Test that pagination works correctly"""
        # Create 60 trademarks to test pagination (50 per page)
        for i in range(60):
            Trademark.objects.create(
                keyword=f"TESTMARK{i}",
                registration_number=f"REG{i}",
                serial_number=f"SER{i}",
                filing_date=date(2023, 1, 1),
            )

        # Search for all test marks
        response = self.client.get(reverse("trademark_local_search"), {"q": "TESTMARK"})
        self.assertEqual(response.status_code, 200)

        # Check that pagination is present
        self.assertContains(response, "Page 1 of")

        # Check that there's a next page link
        self.assertContains(response, "Next")
