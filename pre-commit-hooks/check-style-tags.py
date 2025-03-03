#!/usr/bin/env python
import re
import subprocess
import sys
from pathlib import Path


def get_staged_files():
    """Get list of staged HTML files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f for f in result.stdout.splitlines() if f.endswith(".html")]
    except subprocess.CalledProcessError:
        print("Error: Failed to get staged files from git")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Git command not found")
        sys.exit(1)


def check_style_tags(files):
    """Check if any staged HTML files contain <style> tags"""
    pattern = re.compile(r"<style\b", re.IGNORECASE)
    flagged_files = set()

    for file in files:
        try:
            path = Path(file)
            if not path.exists():
                continue

            with path.open("r", encoding="utf-8") as f:
                content = f.read()
                if pattern.search(content):
                    flagged_files.add(file)
        except (IOError, UnicodeDecodeError) as e:
            print(f"Warning: Could not read file {file}: {str(e)}")
            continue

    return sorted(flagged_files)


def main():
    if "--allow-styles" in sys.argv:
        print("Bypassing <style> tag check.")
        sys.exit(0)

    staged_files = get_staged_files()
    if not staged_files:
        sys.exit(0)

    flagged_files = check_style_tags(staged_files)
    if flagged_files:
        print("\n❌ Commit blocked: `<style>` tags detected in these files:\n")
        for file in flagged_files:
            print(f"  - {file}")
        print("\n🛠 Remove `<style>` tags or use `git commit --allow-styles` to bypass manually.\n")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
