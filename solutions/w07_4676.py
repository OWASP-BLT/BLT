# website/views/repo.py
import urllib.parse

def get_issue_count(repo_full_name, label=None):
    query = f"repo:{repo_full_name} type:issue state:open"
    if label:
        query += f" label:{urllib.parse.quote(label)}"
    # ... rest of function using encoded query
