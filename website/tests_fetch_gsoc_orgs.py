from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from website.models import Organization


class FetchGsocOrgsCommandTest(TestCase):
    """Test cases for the fetch_gsoc_orgs management command"""

    def setUp(self):
        """Set up test data"""
        self.mock_org_data = [
            {
                "slug": "test-organization",
                "name": "Test Organization",
                "website_url": "https://test-org.com",
                "description": "A test organization for GSoC",
                "tagline": "Testing is awesome",
                "license": "MIT",
                "categories": ["Development"],
                "contributor_guidance_url": "https://test-org.com/contribute",
                "tech_tags": ["Python", "Django"],
                "topic_tags": ["Web Development"],
                "source_code": "https://github.com/test-org",
                "ideas_link": "https://test-org.com/ideas",
                "logo_url": "https://test-org.com/logo.png",
                "contact_links": [
                    {"name": "twitter", "value": "https://twitter.com/testorg"},
                ],
            }
        ]

    @patch("website.management.commands.fetch_gsoc_orgs.requests.get")
    def test_fetch_creates_new_organization(self, mock_get):
        """Test that fetching creates a new organization"""
        # Mock the API call
        mock_api_response = MagicMock()
        mock_api_response.json.return_value = self.mock_org_data
        mock_api_response.raise_for_status = MagicMock()

        # Mock the logo download call
        mock_logo_response = MagicMock()
        mock_logo_response.content = b"fake logo data"
        mock_logo_response.raise_for_status = MagicMock()

        # Return different responses based on the URL
        def get_side_effect(url, *args, **kwargs):
            if "logo" in url:
                return mock_logo_response
            return mock_api_response

        mock_get.side_effect = get_side_effect

        out = StringIO()
        call_command("fetch_gsoc_orgs", "--years", "2024", stdout=out)

        # Check organization was created
        org = Organization.objects.get(url="https://test-org.com")
        self.assertEqual(org.name, "Test Organization")
        self.assertEqual(org.description, "A test organization for GSoC")
        self.assertEqual(org.gsoc_years, "2024")

        # Check tags were added
        self.assertTrue(org.tags.filter(slug="gsoc").exists())
        self.assertTrue(org.tags.filter(slug="gsoc24").exists())

    @patch("website.management.commands.fetch_gsoc_orgs.requests.get")
    def test_fetch_updates_existing_organization(self, mock_get):
        """Test that fetching updates an existing organization instead of creating duplicates"""
        # Create an existing organization
        existing_org = Organization.objects.create(
            name="Old Name",
            url="https://test-org.com",
            description="Old description",
            gsoc_years="2023",
        )

        # Mock the API call
        mock_api_response = MagicMock()
        mock_api_response.json.return_value = self.mock_org_data
        mock_api_response.raise_for_status = MagicMock()

        # Mock the logo download call
        mock_logo_response = MagicMock()
        mock_logo_response.content = b"fake logo data"
        mock_logo_response.raise_for_status = MagicMock()

        # Return different responses based on the URL
        def get_side_effect(url, *args, **kwargs):
            if "logo" in url:
                return mock_logo_response
            return mock_api_response

        mock_get.side_effect = get_side_effect

        out = StringIO()
        call_command("fetch_gsoc_orgs", "--years", "2024", stdout=out)

        # Check that only one organization exists
        self.assertEqual(Organization.objects.filter(url="https://test-org.com").count(), 1)

        # Check the organization was updated
        org = Organization.objects.get(url="https://test-org.com")
        self.assertEqual(org.name, "Test Organization")  # Name should be updated
        self.assertEqual(org.description, "A test organization for GSoC")

        # Check years were properly updated
        years = [int(y) for y in org.gsoc_years.split(",")]
        self.assertIn(2023, years)
        self.assertIn(2024, years)

    @patch("website.management.commands.fetch_gsoc_orgs.requests.get")
    def test_fetch_prevents_duplicate_years(self, mock_get):
        """Test that fetching the same year twice doesn't duplicate years"""
        # Mock the API call
        mock_api_response = MagicMock()
        mock_api_response.json.return_value = self.mock_org_data
        mock_api_response.raise_for_status = MagicMock()

        # Mock the logo download call
        mock_logo_response = MagicMock()
        mock_logo_response.content = b"fake logo data"
        mock_logo_response.raise_for_status = MagicMock()

        # Return different responses based on the URL
        def get_side_effect(url, *args, **kwargs):
            if "logo" in url:
                return mock_logo_response
            return mock_api_response

        mock_get.side_effect = get_side_effect

        out = StringIO()
        # Fetch twice for the same year
        call_command("fetch_gsoc_orgs", "--years", "2024", stdout=out)
        call_command("fetch_gsoc_orgs", "--years", "2024", stdout=out)

        org = Organization.objects.get(url="https://test-org.com")
        # Should only have 2024 once
        self.assertEqual(org.gsoc_years, "2024")
        years = [int(y) for y in org.gsoc_years.split(",")]
        self.assertEqual(years.count(2024), 1)

    @patch("website.management.commands.fetch_gsoc_orgs.requests.get")
    def test_fetch_sorts_years_descending(self, mock_get):
        """Test that years are stored in descending order"""
        # Create organization with year 2022
        Organization.objects.create(
            name="Test Organization",
            url="https://test-org.com",
            gsoc_years="2022",
        )

        # Mock the API call
        mock_api_response = MagicMock()
        mock_api_response.json.return_value = self.mock_org_data
        mock_api_response.raise_for_status = MagicMock()

        # Mock the logo download call
        mock_logo_response = MagicMock()
        mock_logo_response.content = b"fake logo data"
        mock_logo_response.raise_for_status = MagicMock()

        # Return different responses based on the URL
        def get_side_effect(url, *args, **kwargs):
            if "logo" in url:
                return mock_logo_response
            return mock_api_response

        mock_get.side_effect = get_side_effect

        out = StringIO()
        # Add years 2024 and 2023
        call_command("fetch_gsoc_orgs", "--years", "2024", stdout=out)
        call_command("fetch_gsoc_orgs", "--years", "2023", stdout=out)

        org = Organization.objects.get(url="https://test-org.com")
        years = [int(y) for y in org.gsoc_years.split(",")]

        # Years should be in descending order
        self.assertEqual(years, [2024, 2023, 2022])

    @patch("website.management.commands.fetch_gsoc_orgs.requests.get")
    def test_fetch_handles_organization_without_url(self, mock_get):
        """Test that organizations without URLs are handled correctly"""
        org_data_no_url = self.mock_org_data[0].copy()
        org_data_no_url["website_url"] = ""

        # Mock the API call
        mock_api_response = MagicMock()
        mock_api_response.json.return_value = [org_data_no_url]
        mock_api_response.raise_for_status = MagicMock()

        # Mock the logo download call
        mock_logo_response = MagicMock()
        mock_logo_response.content = b"fake logo data"
        mock_logo_response.raise_for_status = MagicMock()

        # Return different responses based on the URL
        def get_side_effect(url, *args, **kwargs):
            if "logo" in url:
                return mock_logo_response
            return mock_api_response

        mock_get.side_effect = get_side_effect

        out = StringIO()
        call_command("fetch_gsoc_orgs", "--years", "2024", stdout=out)

        # Should use slug for create/update
        org = Organization.objects.get(slug="test-organization")
        self.assertEqual(org.name, "Test Organization")
        self.assertEqual(org.gsoc_years, "2024")
