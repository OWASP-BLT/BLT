import asyncio
from datetime import datetime
from urllib.parse import quote_plus

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management import call_command
from django.db import DatabaseError, transaction
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Contributor, GitHubIssue, GitHubReview, Repo, UserProfile


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
            if fetch_all_blt:
                await sync_to_async(call_command)("fetch_gsoc_prs")
            return

        self.stdout.write(f"Found {len(users_with_github)} users. Syncing since {since_date_str}")
        semaphore = asyncio.Semaphore(5)
        merged_pr_counts = {}

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            client.headers.update(
                {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {settings.GITHUB_TOKEN}"}
            )

            for index, user in enumerate(users_with_github, 1):
                raw_url = (user.github_url or "").strip().rstrip("/")
                github_username = raw_url.split("/")[-1] if raw_url else None
                if not github_username:
                    continue

                self.stdout.write(f"[{index}/{len(users_with_github)}] Syncing: {github_username}")
                query = f"author:{github_username} type:pr is:merged merged:>={since_date_str}"
                prs = await self._fetch_prs(client, query)
                if not prs:
                    continue

                tasks = [self._process_pr_data(client, pr, semaphore) for pr in prs]
                enriched_data = await asyncio.gather(*tasks)
                success_count = await sync_to_async(self._save_to_db)(user, enriched_data)
                merged_pr_counts[user.id] = success_count

        await sync_to_async(self._update_user_ranks)(users_with_github, merged_pr_counts)
        if fetch_all_blt:
            await sync_to_async(call_command)("fetch_gsoc_prs")

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
            except (httpx.HTTPError, AttributeError):
                break
        return all_items

    async def _process_pr_data(self, client, pr, semaphore):
        pr_url = pr.get("pull_request", {}).get("url")
        if not pr_url:
            return None
        async with semaphore:
            try:
                p_task, r_task = client.get(pr_url), client.get(f"{pr_url}/reviews")
                p_res, r_res = await asyncio.gather(p_task, r_task)
                return {
                    "full_pr": p_res.json() if p_res.status_code == 200 else {},
                    "reviews": r_res.json() if r_res.status_code == 200 else [],
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
                    repo = Repo.objects.get(repo_url__iexact=repo_url)
                    gh_user = pr["user"]
                    contributor, _ = Contributor.objects.get_or_create(
                        github_id=gh_user["id"],
                        defaults={
                            "name": gh_user["login"],
                            "github_url": gh_user["html_url"],
                            "avatar_url": gh_user.get("avatar_url", ""),
                            "contributor_type": gh_user.get("type", "User"),
                        },
                    )
                    repo.contributor.add(contributor)
                    m_at = pr.get("merged_at")
                    github_issue, _ = GitHubIssue.objects.update_or_create(
                        issue_id=pr["number"],
                        repo=repo,
                        defaults={
                            "title": pr["title"],
                            "state": pr["state"],
                            "type": "pull_request",
                            "created_at": self._parse_date(pr["created_at"]),
                            "updated_at": self._parse_date(pr.get("updated_at")),
                            "merged_at": self._parse_date(m_at),
                            "is_merged": bool(m_at),
                            "url": pr["html_url"],
                            "user_profile": user,
                            "contributor": contributor,
                        },
                    )
                    for rev in data["reviews"]:
                        rev_u = rev.get("user")
                        if not rev_u or rev_u.get("type") == "Bot":
                            continue
                        rc, _ = Contributor.objects.get_or_create(
                            github_id=rev_u["id"],
                            defaults={"name": rev_u["login"], "github_url": rev_u.get("html_url", "")},
                        )
                        GitHubReview.objects.update_or_create(
                            review_id=rev["id"],
                            defaults={
                                "pull_request": github_issue,
                                "reviewer_contributor": rc,
                                "state": rev["state"],
                                "submitted_at": self._parse_date(rev.get("submitted_at")),
                                "url": rev.get("html_url", ""),
                            },
                        )
                    count += 1
            except (Repo.DoesNotExist, DatabaseError):
                continue
        return count

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            return timezone.make_aware(datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            return None

    def _update_user_ranks(self, users, merged_pr_counts):
        for user in users:
            # [cite_start]SENTRY FIX: Only update if we actually found updates to preserve history [cite: 600]
            if user.id in merged_pr_counts:
                user.merged_pr_count = merged_pr_counts[user.id]
        UserProfile.objects.bulk_update(users, ["merged_pr_count"])
        sorted_profiles = list(
            UserProfile.objects.exclude(github_url="").exclude(github_url=None).order_by("-merged_pr_count")
        )
        for rank, profile in enumerate(sorted_profiles, 1):
            profile.contribution_rank = rank
        UserProfile.objects.bulk_update(sorted_profiles, ["contribution_rank"])
