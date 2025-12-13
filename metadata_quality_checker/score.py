def calculate_score(project: dict) -> int:
    score = 0

    if project.get("name"):
        score += 10

    if isinstance(project.get("tags"), list) and len(project["tags"]) >= 2:
        score += 25

    if project.get("type"):
        score += 15

    if project.get("level"):
        score += 15

    pitch = project.get("pitch", "")
    if pitch and len(pitch) >= 30:
        score += 20

    if project.get("last_commit"):
        score += 15

    return score


def get_status(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 50:
        return "needs improvement"
    return "poor"

