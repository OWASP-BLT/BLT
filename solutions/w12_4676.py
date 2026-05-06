# website/views/repo.py

import urllib.parse

def get_issue_count(repo_full_name, label=None, state='open'):
    base_url = f"https://api.github.com/search/issues?q=repo:{repo_full_name}"
    if label:
        encoded_label = urllib.parse.quote(label)
        base_url += f"+label:{encoded_label}"
    if state:
        base_url += f"+state:{state}"
    # ... rest of function
