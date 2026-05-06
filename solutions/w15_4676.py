# website/views/repo.py
import urllib.parse

def get_issue_count(repo_full_name, label=None):
    query = f"repo:{repo_full_name}"
    if label:
        query += f" label:{label}"
    encoded_query = urllib.parse.quote(query, safe='')
    url = f"https://api.github.com/search/issues?q={encoded_query}"
    # ... rest of function
