# website/views/repo.py
import urllib.parse

def get_issue_count(repo_name, labels=None, state='open'):
    query_parts = [f'repo:{repo_name}']
    if labels:
        # Properly encode each label to handle special characters
        encoded_labels = [urllib.parse.quote(label, safe='') for label in labels]
        query_parts.append(f'label:{" ".join(encoded_labels)}')
    if state:
        query_parts.append(f'state:{state}')
    
    query = ' '.join(query_parts)
    # URL encode the entire query string
    encoded_query = urllib.parse.quote(query, safe='')
    return f'https://api.github.com/search/issues?q={encoded_query}'
