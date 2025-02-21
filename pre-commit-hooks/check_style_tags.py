import re
import subprocess
import sys

# Argument to allow bypassing the check
ALLOW_BYPASS = "--allow-styles" in sys.argv


def get_staged_files():
    """Get list of staged HTML files"""
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    return [f for f in result.stdout.splitlines() if f.endswith(".html")]


def check_style_tags(files):
    """Check if any staged HTML files contain <style> tags"""
    pattern = re.compile(r"<style\b", re.IGNORECASE)
    flagged_files = []

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            if pattern.search(content):
                flagged_files.append(file)

    return flagged_files


def main():
    if ALLOW_BYPASS:
        print("Bypassing <style> tag check.")
        sys.exit(0)

    staged_files = get_staged_files()
    if not staged_files:
        sys.exit(0)  # No staged HTML files, exit normally

    flagged_files = check_style_tags(staged_files)
    if flagged_files:
        print("\n Commit blocked. <style> tags detected in these files:")
        for file in flagged_files:
            print(f"  - {file}")
        print("\n Remove <style> tags or use `git commit --allow-styles` to bypass manually.\n")
        sys.exit(1)

    print("No <style> tags found. Proceeding with commit.")
    sys.exit(0)


if __name__ == "__main__":
    main()
