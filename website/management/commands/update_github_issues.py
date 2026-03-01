import asyncio
import json
import logging
from datetime import datetime, timezone as dt_timezone
from urllib.parse import quote_plus

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management import call_command
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Contributor, GitHubIssue, GitHubReview, Repo, UserProfile

logger = logging.getLogger(__name__)


def _normalize_github_username(github_url: str) -> str | None:
    """Extract GitHub username from a profile URL, stripping query strings and fragments."""
    raw = (github_url or "").strip().rstrip("/")
    if not raw:
        return None
    username = raw.split("/")[-1].split("?")[0].split("#")[0]
    return username or None


class Command(LoggedBaseCommand):
    help = "Fetches and updates GitHub issue and review data for users"

    def add_arguments(self, parser):
        parser.add_argument("--all-blt-repos", action="store_true")

    def handle(self, *_, **options):
        asyncio.run(self.async_handle(options))

    async def async_handle(self, options):
        fetch_all_blt = options.get("all_blt_repos", False)
        from dateutil.relativedelta import relativedelta

        since_date = timezone.now() - relativedelta(months=6)
        since_date_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        users_with_github = await sync_to_async(
            lambda: list(UserProfile.objects.exclude(github_url="").exclude(github_url=None))
        )()

        if not users_with_github:
            self.stdout.write(self.style.WARNING("No users with GitHub URLs found."))
            if fetch_all_blt:
                await sync_to_async(call_command)("fetch_gsoc_prs")
            return

        self.stdout.write(f"Found {len(users_with_github)} users. Syncing since {since_date_str}")
        semaphore = asyncio.Semaphore(5)
        # Initialize all users with 0 so stale counts are cleared for users with no PRs in window
        merged_pr_counts = {user.id: 0 for user in users_with_github}

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            client.headers.update(
                {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {settings.GITHUB_TOKEN}"}
            )

            for index, user in enumerate(users_with_github, 1):
                github_username = _normalize_github_username(user.github_url)

                if not github_username:
                    continue

                self.stdout.write(f"[{index}/{len(users_with_github)}] Syncing: {github_username}")
                query = f"author:{github_username} type:pr is:merged merged:>={since_date_str}"
                prs = await self._fetch_prs(client, query)

                if not prs:
                    continue

                enriched_data = []
                batch_size = 100
                for start in range(0, len(prs), batch_size):
                    batch = prs[start : start + batch_size]
                    tasks = [self._process_pr_data(client, pr, semaphore) for pr in batch]
                    batch_results = await asyncio.gather(*tasks)
                    enriched_data.extend(batch_results)

                success_count = await sync_to_async(self._save_to_db)(user, enriched_data)
                merged_pr_counts[user.id] = success_count

        await sync_to_async(self._update_user_ranks)(users_with_github, merged_pr_counts)
        if fetch_all_blt:
            await sync_to_async(call_command)("fetch_gsoc_prs")
        self.stdout.write(self.style.SUCCESS("GitHub data fetch completed!"))

    async def _fetch_prs(self, client, query):
        all_items = []
        api_url = f"https://api.github.com/search/issues?q={quote_plus(query)}&per_page=100"
        while api_url:
            try:
                resp = await client.get(api_url)
                resp.raise_for_status()
                data = resp.json()
                all_items.extend(data.get("items", []))
                link_header = resp.headers.get("Link", "")
                api_url = None
                if link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            api_url = part.split(";")[0].strip("< >")
                            break
            except (httpx.HTTPError, json.JSONDecodeError, AttributeError) as exc:
                logger.warning(
                    "Failed to fetch GitHub PR search page. query=%r url=%r error=%s",
                    query,
                    api_url,
                    exc,
                    exc_info=True,
                )
                break
        return all_items

    async def _fetch_all_pages(self, client, url: str) -> list:
        """Fetch all pages from a paginated GitHub API endpoint using Link headers."""
        all_items = []
        next_url = url
        while next_url:
            try:
                resp = await client.get(next_url)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list):
                    all_items.extend(data)
                else:
                    all_items.extend(data.get("items", []))
                link_header = resp.headers.get("Link", "")
                next_url = None
                if link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            next_url = part.split(";")[0].strip("< >")
                            break
            except (httpx.HTTPError, json.JSONDecodeError, AttributeError):
                break
        return all_items

    async def _process_pr_data(self, client, pr, semaphore):
        """Each request acquires semaphore independently — truly bounded to 5."""
        pr_url = pr.get("pull_request", {}).get("url")
        if not pr_url:
            return None

        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await client.get(url)

        try:
            p_res, _ = await asyncio.gather(
                fetch_with_semaphore(pr_url),
                asyncio.sleep(0),  # placeholder — reviews fetched with pagination below
            )
            try:
                full_pr = p_res.json() if p_res.status_code == 200 else {}
            except (json.JSONDecodeError, ValueError):
                logger.warning("Failed to decode JSON for PR URL: %s (status %s)", pr_url, p_res.status_code)
                full_pr = {}

            # Paginate reviews — GitHub default page size is 30, PRs can have many reviews
            async with semaphore:
                reviews = await self._fetch_all_pages(client, f"{pr_url}/reviews?per_page=100")

            return {
                "search_item": pr,
                "full_pr": full_pr,
                "reviews": reviews,
            }
        except httpx.HTTPError:
            return None

    def _save_to_db(self, user, enriched_data):
        count = 0
        for data in enriched_data:
            if not data or not data.get("full_pr"):
                continue

            pr = data["full_pr"]
            repo_url = pr.get("base", {}).get("repo", {}).get("html_url")

            if not repo_url:
                continue

            try:
                with transaction.atomic():
                    # Handle multiple case-variant repo URLs explicitly — log and skip
                    # rather than silently picking an arbitrary match.
                    repos_qs = Repo.objects.filter(repo_url__iexact=repo_url)
                    repo_count = repos_qs.count()
                    if repo_count == 0:
                        # PR is from a repo not tracked in BLT — skip silently
                        continue
                    if repo_count > 1:
                        logger.warning(
                            "Multiple Repo entries match repo_url %s case-insensitively; "
                            "skipping PR #%s for user %s",
                            repo_url,
                            pr.get("number"),
                            user.github_url,
                        )
                        continue
                    repo = repos_qs.first()

                    gh_user = pr["user"]

                    contributor, contributor_created = Contributor.objects.get_or_create(
                        github_id=gh_user["id"],
                        defaults={
                            "name": gh_user["login"],
                            "github_url": gh_user["html_url"],
                            "avatar_url": gh_user.get("avatar_url", ""),
                            "contributor_type": gh_user.get("type", "User"),
                            "contributions": 0,
                        },
                    )
                    if not contributor_created:
                        Contributor.objects.filter(pk=contributor.pk).update(
                            name=gh_user["login"],
                            github_url=gh_user["html_url"],
                            avatar_url=gh_user.get("avatar_url", ""),
                        )
                        contributor.refresh_from_db()

                    repo.contributor.add(contributor)
                    m_at = pr.get("merged_at")
                    github_issue, issue_created = GitHubIssue.objects.update_or_create(
                        issue_id=pr["number"],
                        repo=repo,
                        defaults={
                            "title": pr["title"],
                            "body": pr.get("body", "") or "",
                            "state": pr["state"],
                            "type": "pull_request",
                            "created_at": self._parse_date(pr.get("created_at")),
                            "updated_at": self._parse_date(pr.get("updated_at")),
                            "closed_at": self._parse_date(pr.get("closed_at")),
                            "merged_at": self._parse_date(m_at),
                            "is_merged": bool(m_at),
                            "url": pr["html_url"],
                            "user_profile": user,
                            "contributor": contributor,
                        },
                    )

                    if issue_created:
                        Contributor.objects.filter(pk=contributor.pk).update(
                            contributions=F("contributions") + 1,
                        )
                        contributor.refresh_from_db()

                    for rev in data["reviews"]:
                        rev_u = rev.get("user")
                        if not rev_u or rev_u.get("type") == "Bot":
                            continue

                        submitted_at = self._parse_date(rev.get("submitted_at"))
                        if submitted_at is None:
                            continue

                        rc, rc_created = Contributor.objects.get_or_create(
                            github_id=rev_u["id"],
                            defaults={
                                "name": rev_u["login"],
                                "github_url": rev_u.get("html_url", ""),
                                "avatar_url": rev_u.get("avatar_url", ""),
                                "contributor_type": rev_u.get("type", "User"),
                                "contributions": 0,
                            },
                        )
                        if not rc_created:
                            Contributor.objects.filter(pk=rc.pk).update(
                                name=rev_u["login"],
                                github_url=rev_u.get("html_url", ""),
                                avatar_url=rev_u.get("avatar_url", ""),
                            )
                            rc.refresh_from_db()

                        reviewer_profile = UserProfile.objects.filter(
                            github_url=rev_u.get("html_url", "")
                        ).first()

                        _, review_created = GitHubReview.objects.update_or_create(
                            review_id=rev["id"],
                            defaults={
                                "pull_request": github_issue,
                                "reviewer_contributor": rc,
                                "reviewer": reviewer_profile,
                                "state": rev["state"],
                                "submitted_at": submitted_at,
                                "url": rev.get("html_url", ""),
                                "body": rev.get("body", "") or "",
                            },
                        )

                        if review_created:
                            Contributor.objects.filter(pk=rc.pk).update(
                                contributions=F("contributions") + 1,
                            )
                            rc.refresh_from_db()

                    count += 1
            except DatabaseError:
                logger.exception(
                    "DatabaseError saving PR #%s from repo %s for user %s",
                    pr.get("number"),
                    repo_url,
                    user.github_url,
                )
                continue
        return count

    def _parse_date(self, date_str):
        """Parse a GitHub ISO8601 UTC timestamp ('Z' suffix) into an aware UTC datetime."""
        if not date_str:
            return None
        try:
            # GitHub always returns UTC. Parse explicitly as UTC to avoid
            # shifting timestamps when settings.TIME_ZONE is not UTC.
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=dt_timezone.utc
            )
        except ValueError:
            return None

    def _update_user_ranks(self, users, merged_pr_counts):
        # NOTE: merged_pr_count reflects a ROLLING 6-MONTH WINDOW, not a cumulative all-time count.
        for user in users:
            if user.id in merged_pr_counts:
                user.merged_pr_count = merged_pr_counts[user.id]
        UserProfile.objects.bulk_update(users, ["merged_pr_count"])
        sorted_profiles = list(
            UserProfile.objects.exclude(github_url="").exclude(github_url=None).order_by("-merged_pr_count")
        )
        for rank, profile in enumerate(sorted_profiles, 1):
            profile.contribution_rank = rank
        UserProfile.objects.bulk_update(sorted_profiles, ["contribution_rank"])