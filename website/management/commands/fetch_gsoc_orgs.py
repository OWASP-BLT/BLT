import logging

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

GSoC_API_URL = "https://summerofcode.withgoogle.com/api/program/2025/organizations/"


class Command(BaseCommand):
    help = "Fetches organizations from Google Summer of Code and stores them in the database."

    def handle(self, *args, **kwargs):
        logger.info(f"{COLOR_BLUE}Fetching organizations from GSoC 2025 API...{COLOR_RESET}")

        try:
            response = requests.get(GSoC_API_URL, headers={"User-Agent": "GSOC-Fetcher/1.0"})
            response.raise_for_status()
            organizations = response.json()
        except requests.RequestException as e:
            logger.error(f"{COLOR_RED}Error fetching data from GSoC API: {str(e)}{COLOR_RESET}")
            return

        for org_data in organizations:
            self.process_organization(org_data)

        logger.info(f"{COLOR_GREEN}Finished fetching organizations!{COLOR_RESET}")

    def process_organization(self, org_data):
        data = org_data
        slug = slugify(data["slug"])

        try:
            org, created = Organization.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "description": data.get("description", "")[:500],
                    "url": data.get("website_url"),
                    "tagline": data.get("tagline", ""),
                    "license": data.get("license", ""),
                    "categories": data.get("categories") or None,
                    "contributor_guidance_url": data.get("contributor_guidance_url", ""),
                    "tech_tags": data.get("tech_tags") or None,
                    "topic_tags": data.get("topic_tags") or None,
                    "source_code": data.get("website_url"),
                    "is_active": True,
                },
            )

            # Handle Logo
            if data.get("logo_url"):
                self.download_logo(data["logo_url"], org, slug)

            # Handle Tags (tech_tags + topic_tags)
            self.assign_tags(org, data.get("tech_tags", []) + data.get("topic_tags", []))

            # Handle Contact Links
            self.assign_contacts(org, data.get("contact_links", []))

            org.save()
            status = "Added" if created else "Updated"
            logger.info(f"{COLOR_GREEN}{status}: {data['name']}{COLOR_RESET}")

        except Exception as e:
            logger.error(f"{COLOR_RED}Failed to save {data['name']}: {str(e)}{COLOR_RESET}")

    def download_logo(self, logo_url, org, slug):
        """Downloads and saves the organization’s logo."""
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

    def assign_contacts(self, org, contacts):
        for contact in contacts:
            if contact["name"].lower() == "email":
                org.email = contact["value"]
            elif contact["name"].lower() == "chat":
                org.twitter = contact["value"]  # Adjust this if needed

        org.save()
