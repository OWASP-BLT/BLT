import logging

logger = logging.getLogger(__name__)


class PullRequest:
    def __init__(self, payload):
        """Responsible for creating a PR object for convenience.
        Doesn't check for keys in payload - it is assumed to have been verified beforehand.
        """
        self.action: str = payload["action"]
        self.number: int = payload["number"]
        self.api_url: str = payload["pull_request"]["url"]
        self.diff_url: str = payload["pull_request"]["diff_url"]
        self.files_url: str = self.api_url + "/files"
        self.comments_url: str = payload["pull_request"]["comments_url"]
        self.id: int = payload["pull_request"]["id"]
        self.state: str = payload["pull_request"]["state"]
        self.author: str = payload["pull_request"]["user"]["login"]
        self.title: str = payload["pull_request"].get("title", "")
        self.body: str = payload["pull_request"].get("body", "")
        self.is_draft: bool = payload["pull_request"].get("draft", False)
        self.head_branch: str = payload["pull_request"]["head"]["ref"]
        self.base_branch: str = payload["pull_request"]["base"]["ref"]
        self.repo_full_name: str = payload["pull_request"]["base"]["repo"]["full_name"]
        self.repo_id: str = payload["pull_request"]["base"]["repo"]["id"]
        self.default_branch: str = payload["pull_request"]["base"]["repo"]["default_branch"]

        self._verify_branch()

    def __repr__(self) -> str:
        return (
            f"<PullRequest "
            f"#{self.number} '{self.title}' "
            f"author={self.author} "
            f"action={self.action} "
            f"state={'draft' if self.is_draft else self.state} "
            f"head={self.head_branch} base={self.base_branch} "
            f"repo={self.repo_full_name}>"
        )

    # Make the error msg more readable, don't crash the entire app
    def _verify_branch(self) -> bool:
        """
        Verify that the PR's base branch matches the repo's default branch.

        This is critical because our semantic search index is based on the default branch.
        If the base is different (e.g. 'feature'), the retrieved context may be outdated or incorrect.

        Returns:
            True if base matches default branch.
            False if mismatch — caller should skip AI-powered review.
        """
        if self.default_branch == self.base_branch:
            return True

        logger.warning(
            "PR #%d: Base branch '%s' != default branch '%s'. "
            "Skipping AI-powered code review because semantic search is indexed on '%s'. "
            "To enable AI review, target '%s' or rebase onto it. Support for non-default bases is coming.",
            self.number,
            self.base_branch,
            self.default_branch,
            self.default_branch,
            self.default_branch,
        )
        return False
