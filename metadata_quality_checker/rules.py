from datetime import datetime, timedelta


def check_rules(project: dict) -> list[str]:
    issues = []

    if not project.get("name"):
        issues.append("Missing project name")

    tags = project.get("tags", [])
    if not isinstance(tags, list) or len(tags) < 2:
        issues.append("Missing or insufficient tags")

    if not project.get("type"):
        issues.append("Missing project type")

    if not project.get("level"):
        issues.append("Missing difficulty level")

    pitch = project.get("pitch", "")
    if not pitch or len(pitch) < 30:
        issues.append("Pitch too short or missing")

    if not project.get("repo_url"):
        issues.append("Missing repository URL")

    last_commit = project.get("last_commit")
    if last_commit:
        try:
            commit_date = datetime.fromisoformat(last_commit)
            if commit_date < datetime.now() - timedelta(days=365):
                issues.append("Project inactive (no commits in last 12 months)")
        except ValueError:
            issues.append("Invalid last_commit date format")
    else:
        issues.append("Missing activity data")

    return issues
