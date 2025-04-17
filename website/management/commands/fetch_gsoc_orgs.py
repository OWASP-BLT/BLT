import logging
import re

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from website.models import Organization, Tag

# ANSI escape codes for colors
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"

logger = logging.getLogger(__name__)

# Base API URL for GSoC organizations
GSOC_API_BASE_URL = "https://summerofcode.withgoogle.com/api/archive/programs/{year}/organizations/"

# Years to fetch (update this list as needed)
GSOC_YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]


class Command(BaseCommand):
    help = (
        "Fetches organizations from Google Summer of Code (current and previous years) and stores them in the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--years",
            nargs="+",
            type=int,
            help="Specific years to fetch (e.g., --years 2025 2024 2023). If not specified, all configured years will be fetched.",
        )
        parser.add_argument("--current-only", action="store_true", help="Fetch only the current year (2025)")

    def handle(self, *args, **kwargs):
        years_to_fetch = kwargs.get("years")
        current_only = kwargs.get("current_only")

        if current_only:
            years_to_fetch = [GSOC_YEARS[0]]  # Only fetch the most recent year (2025)
        elif not years_to_fetch:
            years_to_fetch = GSOC_YEARS  # Fetch all years if not specified

        total_orgs = 0

        for year in years_to_fetch:
            orgs_count = self.fetch_organizations_for_year(year)
            if orgs_count:
                total_orgs += orgs_count

        logger.info(
            f"{COLOR_GREEN}Finished fetching organizations! Total: {total_orgs} organizations from {len(years_to_fetch)} years{COLOR_RESET}"
        )

    def fetch_organizations_for_year(self, year):
        """Fetch and process organizations for a specific GSoC year."""
        api_url = GSOC_API_BASE_URL.format(year=year)
        logger.info(f"{COLOR_BLUE}Fetching organizations from GSoC {year} API...{COLOR_RESET}")

        try:
            response = requests.get(api_url, headers={"User-Agent": "GSOC-Fetcher/1.0"})
            response.raise_for_status()
            organizations = response.json()

            logger.info(f"{COLOR_GREEN}Found {len(organizations)} organizations for GSoC {year}{COLOR_RESET}")

            for org_data in organizations:
                self.process_organization(org_data, year)

            return len(organizations)

        except requests.RequestException as e:
            logger.error(f"{COLOR_RED}Error fetching data from GSoC {year} API: {str(e)}{COLOR_RESET}")
            return 0

    def process_organization(self, org_data, year):
        data = org_data
        slug = slugify(data["slug"])
        url = data.get("website_url", "")

        try:
            # First check if an organization with the same URL exists
            existing_orgs = Organization.objects.filter(url=url) if url else None

            if existing_orgs and existing_orgs.exists():
                # Organization with same URL already exists, update it instead of creating a new one
                org = existing_orgs.first()
                # Update basic info in case it changed
                org.name = data["name"]
                org.description = data.get("description", "")[:500]
                org.tagline = data.get("tagline", "")
                org.license = data.get("license", "")
                org.categories = data.get("categories") or []
                org.contributor_guidance_url = data.get("contributor_guidance_url", "")
                org.tech_tags = data.get("tech_tags") or []
                org.topic_tags = data.get("topic_tags") or []
                org.source_code = data.get("source_code", "")
                org.ideas_link = data.get("ideas_link", "")
                org.is_active = True
                created = False
                logger.info(f"{COLOR_BLUE}Found existing organization with same URL: {org.name}{COLOR_RESET}")
            else:
                # No existing organization with this URL, create a new one
                org, created = Organization.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": data["name"],
                        "description": data.get("description", "")[:500],
                        "url": url,
                        "tagline": data.get("tagline", ""),
                        "license": data.get("license", ""),
                        "categories": data.get("categories") or [],
                        "contributor_guidance_url": data.get("contributor_guidance_url", ""),
                        "tech_tags": data.get("tech_tags") or [],
                        "topic_tags": data.get("topic_tags") or [],
                        "source_code": data.get("source_code", ""),
                        "ideas_link": data.get("ideas_link", ""),
                        "is_active": True,
                    },
                )

            # Handle Logo - only download if this is a newly created org or it doesn't have a logo yet
            if data.get("logo_url") and (created or not org.logo):
                self.download_logo(data["logo_url"], org, slug)

            # Handle Tags (tech_tags + topic_tags)
            self.assign_tags(org, data.get("tech_tags", []) + data.get("topic_tags", []))

            # Add year-specific tag
            year_tag_slug = f"gsoc{str(year)[2:]}"
            year_tag_name = f"GSoC {year}"
            year_tag, _ = Tag.objects.get_or_create(slug=year_tag_slug, defaults={"name": year_tag_name})
            org.tags.add(year_tag)

            # Handle Contact Links
            self.assign_contacts(org, data.get("contact_links", []))

            # Add a field to track participation years if it doesn't exist
            if not hasattr(org, "gsoc_years") or not org.gsoc_years:
                org.gsoc_years = []

            # Add this year to the organization's participation history if not already there
            if year not in org.gsoc_years:
                org.gsoc_years.append(year)
                org.gsoc_years.sort(reverse=True)  # Most recent years first

            org.save()
            status = "Added" if created else "Updated"
            logger.info(f"{COLOR_GREEN}{status}: {data['name']} (GSoC {year}){COLOR_RESET}")

        except Exception as e:
            logger.error(f"{COLOR_RED}Failed to save {data['name']} (GSoC {year}): {str(e)}{COLOR_RESET}")

    def download_logo(self, logo_url, org, slug):
        """Downloads and saves the organization's logo."""
        try:
            response = requests.get(logo_url)
            response.raise_for_status()

            logo_path = f"{slug}.png"
            if default_storage.exists(logo_path):
                default_storage.delete(logo_path)

            org.logo.save(logo_path, ContentFile(response.content))
            logger.info(f"{COLOR_BLUE}Downloaded logo for {org.name}{COLOR_RESET}")

        except requests.RequestException as e:
            logger.warning(f"{COLOR_YELLOW}Failed to download logo for {org.name}: {str(e)}{COLOR_RESET}")

    def assign_tags(self, org, tags):
        """Assigns tags to an organization."""
        for tag_name in tags:
            tag_slug = slugify(tag_name)
            tag, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={"name": tag_name})
            org.tags.add(tag)

        # Add a general GSoC tag
        gsoc_tag, _ = Tag.objects.get_or_create(slug="gsoc", defaults={"name": "Google Summer of Code"})
        org.tags.add(gsoc_tag)

    def assign_contacts(self, org, social_links):
        social_mapping = {
            "matrix": "matrix_url",
            "slack": "slack_url",
            "discord": "discord_url",
            "gitter": "gitter_url",
            "zulipchat": "zulipchat_url",
            "element": "element_url",
            "twitter": "twitter",
            "facebook": "facebook",
        }

        for link in social_links:
            name = link.get("name", "").lower()
            value = link.get("value", "")
            if name in social_mapping:
                if name == "twitter":
                    match = re.search(r"twitter\.com/([A-Za-z0-9_]+)", value)
                    org.twitter = match.group(1) if match else ""
                else:
                    setattr(org, social_mapping[name], value)
            elif "element" + ".io" in value:
                org.element_url = value
            elif "gitter" + ".im" in value:
                org.gitter_url = value
            elif "discord" in value:
                org.discord_url = value
            org.save()
