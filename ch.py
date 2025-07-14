import logging
import os
from typing import Optional

from django.conf import settings

settings.configure(BASE_DIR=os.path.dirname(os.path.dirname(__file__)))


SKIP_DIRS = {"migrations", "__pycache__", "staticfiles", "static", "media", "site-packages"}

logger = logging.getLogger(__name__)

print("Working directory:", os.getcwd())


def _should_skip_file(file: str) -> bool:
    return not file.endswith(".html")


def _read_file(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, UnicodeDecodeError) as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def chunk_html_file(content: str, file_path: str):
    return content


def process_file(file_path: str):
    content = _read_file(file_path)
    if not content:
        return

    chunks = chunk_html_file(content, file_path)
    print(chunks)


repo_root = os.getcwd()
file_paths = []
for root, dirs, files in os.walk(repo_root):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for file in files:
        if _should_skip_file(file):
            continue
        file_path = os.path.join(root, file)
        rel_path = os.path.relpath(file_path, repo_root)
        file_paths.append(rel_path)

# print(file_paths)
total_files = len(file_paths)
logger.info("Found %d files to process.", total_files)

for i, file_path in enumerate(file_paths, 1):
    process_file(file_path)
    if i % 10 == 0 or i == total_files:
        logger.info("Processed %d/%d files.", i, total_files)
    if i == 5:
        break
