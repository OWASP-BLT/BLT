# website/views/repo.py
import urllib.parse

def get_issue_count(repo_name, label):
    query = f'repo:{repo_name} label:"{label}"'
    encoded_query = urllib.parse.quote(query, safe='')
    url = f'https://api.github.com/search/issues?q={encoded_query}'
    # ... rest of the function
