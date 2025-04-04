import os
import json
import requests
from datetime import datetime, timedelta

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BLT_API_TOKEN = os.getenv("BLT_API_TOKEN")
GITHUB_API = "https://api.github.com"
BLT_API = "https://blt.owasp.org/api"  # Adjust if different
BLT_BASE_URL = "https://blt.owasp.org"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Load event payload
with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event_payload = json.load(f)
repo = event_payload["repository"]["full_name"]
issue = event_payload.get("issue", {})

def get_view_count(issue_number):
    """Fetch view count from IP logs via BLT API for the last 30 days."""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        badge_path = f"/badge/issue/{issue_number}"
        response = requests.get(
            f"{BLT_API}/stats/views",
            headers={"Authorization": f"Bearer {BLT_API_TOKEN}"},
            params={
                "path": badge_path,
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        )
        response.raise_for_status()
        return response.json().get("view_count", 0)
    except Exception as e:
        print(f"Error fetching view count: {e}")
        return 0

def get_bounty_amount(issue_number):
    """Fetch bounty amount from GitHubIssue via BLT API."""
    try:
        response = requests.get(
            f"{BLT_API}/github-issues/{issue_number}",
            headers={"Authorization": f"Bearer {BLT_API_TOKEN}"},
            params={"repo": repo}
        )
        response.raise_for_status()
        data = response.json()
        # Use p2p_amount_usd if available, fallback to 0
        return data.get("p2p_amount_usd", 0) or 0
    except Exception as e:
        print(f"Error fetching bounty: {e}")
        return 0

def generate_badge_url(issue_number, views, bounty):
    """Generate the badge URL with stats as query parameters."""
    return (
        f"{BLT_BASE_URL}/badge/issue/{issue_number}?"
        f"views={views}&bounty={bounty}&t={int(datetime.now().timestamp())}"
    )

def update_issue_description(issue_number, badge_url):
    """Update the issue description with the badge."""
    current_body = issue.get("body", "") or ""
    badge_markdown = f"![BLT Issue Stats]({badge_url})"
    
    # Remove existing badge if present
    if "![BLT Issue Stats](" in current_body:
        lines = current_body.split("\n")
        current_body = "\n".join(line for line in lines if not line.startswith("![BLT Issue Stats]("))
    
    # Add new badge at the top
    new_body = f"{badge_markdown}\n\n{current_body}".strip()
    
    response = requests.patch(
        f"{GITHUB_API}/repos/{repo}/issues/{issue_number}",
        headers=HEADERS,
        json={"body": new_body}
    )
    response.raise_for_status()
    print(f"Updated issue #{issue_number} with badge")

def main():
    if not issue:
        print("No issue found in event payload")
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
