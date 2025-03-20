import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from website.models import OsshDiscussionChannel, Tag


class Command(BaseCommand):
    help = "Fetches public programming-related Discord servers"

    def handle(self, *args, **options):
        token = settings.DISCORD_BOT_TOKEN
        limit = 20

        # Discord API endpoint for server discovery
        url = "https://discord.com/api/v10/discovery/search"
        headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

        # Search parameters for programming-related servers
        search_terms = [
            "programming",
            "coding",
            "developers",
            "software engineering",
            "open source",
            "opensource",
            "open-source projects",
            "FOSS",
            "developer community",
            "software development",
            "coding help",
            "hackathons",
            "tech discussions",
            "CS students",
            "coding challenges",
            "devops",
            "AI developers",
            "machine learning",
            "data science",
            "web development",
            "backend development",
            "frontend development",
            "full stack developers",
            "game development",
            "cybersecurity",
            "blockchain developers",
            "cloud computing",
            "Linux users",
            "GitHub discussions",
            "collaborative coding",
            "tech startups",
            "coding mentorship",
            "bug bounty",
            "ethical hacking",
            "software architecture",
            "API development",
            "low-code/no-code",
            "automation",
            "scripting",
            "Python developers",
            "JavaScript developers",
            "React developers",
            "Django developers",
            "Node.js developers",
            "Rust programming",
            "Go programming",
            "Java developers",
            "C++ programming",
            "Android development",
            "iOS development",
            "open-source contributions",
            "freeCodeCamp",
            "100DaysOfCode",
            "code reviews",
            "pair programming",
            "developer networking",
            "open-source events",
            "open-source maintainers",
            "open-source contributors",
            "community-driven development",
            "open-source foundations",
        ]

        all_servers = set()

        try:
            for term in search_terms:
                params = {"query": term, "limit": limit}

                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                servers = response.json().get("hits", [])

                for server in servers:
                    server_id = server.get("id")

                    if server_id in all_servers:
                        continue

                    all_servers.add(server_id)

                    server_info = {
                        "name": server.get("name", "Unknown"),
                        "description": server.get("description", ""),
                        "member_count": server.get("approximate_member_count", 0),
                        "id": server_id,
                        "logo_url": f"https://cdn.discordapp.com/icons/{server_id}/{server.get('icon')}.png"
                        if server.get("icon")
                        else "",
                        "tags": server.get("keywords", []),
                    }

                    channel, created = OsshDiscussionChannel.objects.update_or_create(
                        external_id=server_info["id"],
                        defaults={
                            "name": server_info["name"],
                            "description": server_info["description"],
                            "source": "Discord",
                            "member_count": server_info["member_count"],
                            "logo_url": server_info["logo_url"],
                        },
                    )

                    for tag_name in server_info["tags"]:
                        slug = slugify(tag_name)

                        tag = Tag.objects.filter(slug=slug).first()

                        if not tag:
                            tag = Tag.objects.create(name=tag_name, slug=slug)

                        channel.tags.add(tag)

                    status = "Created" if created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"\n{'=' * 50}"))
                    self.stdout.write(self.style.SUCCESS(f"{status} Server: {channel.name}"))
                    self.stdout.write(self.style.NOTICE(f"Description: {channel.description[:100]}..."))
                    self.stdout.write(self.style.WARNING(f"Members: {channel.member_count:,}"))
                    self.stdout.write(self.style.SQL_FIELD(f"Server ID: {channel.external_id}"))
                    self.stdout.write(self.style.SQL_FIELD(f"Logo URL: {channel.logo_url}"))
                    self.stdout.write(self.style.NOTICE(f"Tags: {', '.join(tag.name for tag in channel.tags.all())}"))

            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 50}"))
            self.stdout.write(self.style.SUCCESS(f"\nTotal unique servers processed: {len(all_servers)}"))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Error fetching servers: {str(e)}"))
