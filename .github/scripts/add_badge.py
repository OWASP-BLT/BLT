import os
import json
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_API = "https://api.github.com"
BLT_BASE_URL = "https://blt.owasp.org"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

event_path = os.getenv("GITHUB_EVENT_PATH")
if not event_path:
    print("Error: GITHUB_EVENT_PATH environment variable not set")
    exit(1)
try:
    with open(event_path) as f:
        event_payload = json.load(f)
    repo = event_payload.get("repository", {}).get("full_name")
    issue = event_payload.get("issue", {})
    if not repo:
        print("Error: Repository information not found in event payload")
        exit(1)
except Exception as e:
    print(f"Error loading event payload: {e}")
    exit(1)

def get_view_count(issue_number):
    print(f"Warning: No BLT API available for view count of issue #{issue_number}. Using placeholder.")
    return 0

def get_bounty_amount(issue_number):
    print(f"Warning: No BLT API available for bounty of issue #{issue_number}. Using placeholder.")
    return 0

def generate_badge_url(issue_number, views, bounty):
    return (
        f"{BLT_BASE_URL}/badge/issue/{issue_number}?"
        f"views={views}&bounty={bounty}&t={int(datetime.now().timestamp())}"
    )

def update_issue_description(issue_number, badge_url):
    current_body = issue.get("body") or ""
    badge_markdown = f"![BLT Issue Stats]({badge_url})"
    if "![BLT Issue Stats](" in current_body:
        lines = current_body.split("\n")
        current_body = "\n".join(line for line in lines if not line.startswith("![BLT Issue Stats]("))
    new_body = f"{badge_markdown}\n\n{current_body}".strip()
    try:
        response = requests.patch(
            f"{GITHUB_API}/repos/{repo}/issues/{issue_number}",
            headers=HEADERS,
            json={"body": new_body},
            timeout=10
        )
        response.raise_for_status()
        print(f"Updated issue #{issue_number} with badge")
    except requests.RequestException as e:
        print(f"Error updating issue description: {e}")
        exit(1)

def main():
    required_vars = ["GITHUB_TOKEN", "OPENAI_API_KEY", "GITHUB_EVENT_PATH"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    if not issue:
        print("No issue found in event payload")
        return
    if "number" not in issue:
        print("Issue number not found in payload")
        return
    issue_number = issue["number"]
    views = get_view_count(issue_number)
    bounty = get_bounty_amount(issue_number)
    badge_url = generate_badge_url(issue_number, views, bounty)
    update_issue_description(issue_number, badge_url)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in script: {e}")
        exit(1)
