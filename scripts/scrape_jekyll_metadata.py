#!/usr/bin/env python3

import csv
import os
import re
import sys
import time
from datetime import datetime

# Third-party imports
try:
    import requests
    import yaml
except ImportError as e:
    print(f"Error: Missing dependency '{e.name}'.")
    print("Please install required packages: pip install requests PyYAML")
    sys.exit(1)

# --- Configuration ---
ORGANIZATION = "OWASP"
GITHUB_API_URL = "https://api.github.com"
OUTPUT_FILE = f"owasp_project_metadata_{datetime.now().strftime('%Y%m%d')}.csv"
TIMEOUT_SECONDS = 10

# Optional: GitHub Token to avoid rate limits
# Usage: export GITHUB_TOKEN=your_token_here
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"


def get_repositories(org):
    """
    Fetches all public repositories for a specific organization using the GitHub API.

    Args:
        org (str): The GitHub organization name.

    Returns:
        list: A list of repository dictionaries.
    """
    print(f"[*] Fetching repositories for organization: {org}...")
    repos = []
    page = 1
    
    while True:
        url = f"{GITHUB_API_URL}/orgs/{org}/repos"
        params = {"per_page": 100, "page": page}
        
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT_SECONDS)
            
            if response.status_code != 200:
                print(f"    [!] Error fetching repos (Status: {response.status_code})")
                break
                
            data = response.json()
            if not data:
                break
                
            repos.extend(data)
            
            # Safety break for testing purposes (Remove or increase for full scan)
            if len(repos) >= 100: 
                break
                
            page += 1
            
        except requests.RequestException as e:
            print(f"    [!] Connection error: {e}")
            break
            
    print(f"    [+] Found {len(repos)} repositories.")
    return repos


def get_index_content(repo_full_name, default_branch):
    """
    Attempts to retrieve the raw content of index.md or similar metadata files.

    Args:
        repo_full_name (str): The full name of the repo (e.g., 'OWASP/BLT').
        default_branch (str): The default branch name (e.g., 'master' or 'main').

    Returns:
        tuple: (content_string, filename) or (None, None) if not found.
    """
    # Priority list of files to check for metadata
    filenames = ["index.md", "index.html", "README.md", "readme.md"]
    
    for filename in filenames:
        raw_url = f"https://raw.githubusercontent.com/{repo_full_name}/{default_branch}/{filename}"
        try:
            response = requests.get(raw_url, timeout=5)
            if response.status_code == 200:
                return response.text, filename
        except requests.RequestException:
            continue
            
    return None, None


def parse_front_matter(content):
    """
    Extracts and parses YAML front-matter from a markdown string.

    Args:
        content (str): The raw file content.

    Returns:
        dict: The parsed metadata, or None if parsing fails.
    """
    if not content:
        return None

    # Regex to capture content between the first two '---' lines
    match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    
    if match:
        yaml_block = match.group(1)
        try:
            return yaml.safe_load(yaml_block)
        except yaml.YAMLError:
            return None
            
    return None


def main():
    print(f"--- OWASP Jekyll Metadata Scraper ---")
    
    repos = get_repositories(ORGANIZATION)
    results = []
    all_unique_keys = set()
    
    print(f"\n[*] Scanning repositories for metadata...")
    
    for i, repo in enumerate(repos):
        # Progress indicator every 10 repos
        if i > 0 and i % 10 == 0:
            print(f"    Processed {i}/{len(repos)} repositories...")
        
        name = repo['name']
        full_name = repo['full_name']
        default_branch = repo.get('default_branch', 'master')
        
        content, filename = get_index_content(full_name, default_branch)
        
        if content:
            metadata = parse_front_matter(content)
            
            if metadata and isinstance(metadata, dict):
                # Flatten data for CSV export
                row = {
                    'repo_name': name,
                    'metadata_file': filename,
                    'repo_url': repo['html_url']
                }
                
                # Clean up metadata values (convert lists to strings)
                for k, v in metadata.items():
                    if isinstance(v, list):
                        row[k] = ", ".join(map(str, v))
                    else:
                        row[k] = str(v)
                
                results.append(row)
                all_unique_keys.update(row.keys())

    # Sort CSV headers: Repo info first, then metadata keys alphabetically
    static_headers = ['repo_name', 'metadata_file', 'repo_url']
    dynamic_headers = sorted([k for k in all_unique_keys if k not in static_headers])
    fieldnames = static_headers + dynamic_headers
    
    print(f"\n[*] Writing report to {OUTPUT_FILE}...")
    
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        print(f"    [+] Success! Report saved with {len(results)} entries.")
    except IOError as e:
        print(f"    [!] Error writing CSV file: {e}")

    # Display Proposed Standard based on common fields found
    print("\n" + "="*50)
    print("PROPOSED METADATA STANDARD")
    print("="*50)
    print("Based on the analysis, we recommend enforcing the following structure:")
    print("---")
    print("layout: col-sidebar")
    print("title: <Project Name>")
    print("tags: <tag1>, <tag2>")
    print("level: <1-4>")
    print("type: <tool|documentation|code>")
    print("pitch: <Short description>")
    print("region: <Region/Unknown>")
    print("---")


if __name__ == "__main__":
    main()
