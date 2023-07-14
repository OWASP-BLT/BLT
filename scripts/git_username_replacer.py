
"""
    Git Username Replacer: 
    Safeguard user privacy and enhance security by easily replacing usernames in Git commit history.
    Protect sensitive information with our tool.
    
    Use: python git_username_replacer.py <repo path> <old_author_username> <new_author_username>
"""

import os
import argparse
import subprocess

def replace_username(repo_path, old_username, new_username):
    command = [
        'git',
        '-C',
        repo_path,
        'filter-branch',
        '--env-filter',
        f'if [ "$GIT_AUTHOR_NAME" = "{old_username}" ]; then GIT_AUTHOR_NAME="{new_username}"; fi',
        '--tag-name-filter',
        'cat',
        '--',
        '--branches',
        '--tags'
    ]

    try:
        subprocess.run(command, check=True)
        print("Username replaced successfully.")
    except subprocess.CalledProcessError as e:
        print("Error occurred during username replacement.")
        print(e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replace Git Username Tool")
    parser.add_argument("repo_path", help="Path to the Git repository")
    parser.add_argument("old_username", help="Old username to replace")
    parser.add_argument("new_username", help="New username")

    args = parser.parse_args()
    repo_path = args.repo_path
    old_username = args.old_username
    new_username = args.new_username

    if not os.path.exists(repo_path):
        print("Invalid repository path.")
    else:
        replace_username(repo_path, old_username, new_username)