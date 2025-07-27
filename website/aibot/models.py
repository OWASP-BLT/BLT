import json
import logging
from json import JSONDecodeError

from website.aibot.network import fetch_pr_files

logger = logging.getLogger(__name__)


class BranchMismatchError(Exception):
    """Raised when the PR base branch is not the default branch."""

    pass


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
        self.id: int = payload["pull_request"]["id"]
        self.state: str = payload["pull_request"]["state"]
        self.author: str = payload["pull_request"]["user"]["login"]
        self.title: str = payload["pull_request"].get("title", "")
        self.body: str = payload["pull_request"].get("body", "")
        self.is_draft: bool = payload["pull_request"].get("draft", False)
        self.head_branch: str = payload["pull_request"]["head"]["ref"]
        self.base_branch: str = payload["pull_request"]["base"]["ref"]
        self.repo_full_name: str = payload["pull_request"]["base"]["repo"]["full_name"]
        self.default_branch: str = payload["pull_request"]["base"]["repo"]["default_branch"]

        self._verify_branch()
        self._load_pr_files()

    def _verify_branch(self):
        if self.default_branch != self.base_branch:
            logger.error(
                "PR base branch '%s' does not match repo default branch '%s'", self.base_branch, self.default_branch
            )
            raise BranchMismatchError(
                f"PR base branch '{self.base_branch}' does not match repo default branch '{self.default_branch}'"
            )

    def _load_pr_files(self):
        pr_files = fetch_pr_files(self.files_url)
        self.pr_files_json = []
        self.raw_url_map = {}

        if pr_files:
            try:
                self.pr_files_json = json.loads(pr_files)
            except JSONDecodeError as e:
                logger.error("Invalid JSON format for pr files: %s", e)
        else:
            logger.error("Could not fetch the pull request files for: %s", self.files_url)

        for file in self.pr_files_json:
            self.raw_url_map[file["filename"]] = file["raw_url"]
