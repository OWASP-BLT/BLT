# scripts/convert_images_to_webp.py

import shutil
from pathlib import Path

from PIL import Image

# Directories to process
SOURCE_DIRS = [
    "website/static/images",
    "website/static/img",
    "website/static/img/browser-logos",
]

BACKUP_DIR = "website/static/_image_backups"


def ensure_backup_dir():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)


def convert_png(png_path: Path):
    try:
        webp_path = png_path.with_suffix(".webp")

        # Skip if already converted
        if webp_path.exists():
            return

        # Backup original
        rel = png_path.relative_to("website/static")
        backup_path = Path(BACKUP_DIR) / rel
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png_path, backup_path)

        # Convert to WebP
        img = Image.open(png_path).convert("RGBA")
        img.save(webp_path, "webp", quality=85, method=6)

        # Optimize original PNG (overwrite)
        img.save(png_path, optimize=True)

    except Exception:
        # Silent failure by design (CI-safe)
        pass


def main():
    ensure_backup_dir()
    for d in SOURCE_DIRS:
        p = Path(d)
        if not p.exists():
            continue
        for png in p.rglob("*.png"):
            convert_png(png)


if __name__ == "__main__":
    main()
