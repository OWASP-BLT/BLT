import csv
from datetime import datetime, timedelta

import requests

# Configuration
username = "USERNAME"  # GitHub username of the user
repo = "REPOSITORY"  # Repository name
owner = "OWNER"  # Owner of the repository, can be a user or an organization
token = "YOUR_GITHUB_ACCESS_TOKEN"  # Personal Access Token (PAT) for authentication
start_date = "2023-01-01"  # Start date in YYYY-MM-DD format
end_date = "2023-01-31"  # End date in YYYY-MM-DD format
csv_filename = "commit_data.csv"

# Prepare headers for authentication
headers = {"Authorization": f"token {token}"}


# Function to fetch commit counts
def fetch_commit_counts(username, repo, owner, headers, start_date, end_date):
    commit_counts = {}  # Dictionary to store commit counts with dates

    # Convert string dates to datetime objects
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Loop through the date range
    current_date = start_date_dt
    while current_date <= end_date_dt:
        # ISO format the current_date for GitHub API
        since = current_date.isoformat()
        until = (current_date + timedelta(days=1)).isoformat()

        # GitHub API URL to fetch commits for the given date range
        url = f"https://api.github.com/repos/{owner}/{repo}/commits?author={username}&since={since}&until={until}"

        # Make the API request
        response = requests.get(url, headers=headers)
        data = response.json()

        # Store the commit count for the current_date
        commit_counts[current_date.date()] = len(data)

        # Move to the next day
        current_date += timedelta(days=1)

    return commit_counts


# Fetch commit counts
commit_counts = fetch_commit_counts(username, repo, owner, headers, start_date, end_date)

# Write commit counts to CSV
with open(csv_filename, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["day", "commit_count"])

    for day, count in commit_counts.items():
        writer.writerow([day, count])

print(f"Commit data written to {csv_filename}")
