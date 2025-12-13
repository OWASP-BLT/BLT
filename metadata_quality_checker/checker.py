import json
import sys
from pathlib import Path
from rules import check_rules
from score import calculate_score, get_status


def load_metadata():
    # If user passes a file path: python checker.py file.json
    if len(sys.argv) > 1:
        metadata_path = Path(sys.argv[1])
    else:
        # Default to sample file
        metadata_path = Path(__file__).parent / "sample_metadata.json"

    if not metadata_path.exists():
        print(f"❌ Metadata file not found: {metadata_path}")
        sys.exit(1)

    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    metadata = load_metadata()

    print("\n🔍 OWASP Metadata Quality Report\n")

    for project in metadata:
        issues = check_rules(project)
        score = calculate_score(project)
        status = get_status(score)

        name = project.get("name", "Unnamed Project")
        print(f"📦 Project: {name}")
        print(f"📊 Score: {score}/100 ({status})")

        if not issues:
            print("✅ No issues found\n")
        else:
            for issue in issues:
                print(f"❌ {issue}")
            print("")


if __name__ == "__main__":
    main()
