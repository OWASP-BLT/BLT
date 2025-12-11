from pathlib import Path

from PIL import Image

# List of image paths you want to convert (relative to repo root)
TARGET_FILES = [
    "website/static/images/dummy-user.png",
    "website/static/images/bacon.png",
    "website/static/images/googlelogo_color_272x92dp.png",
    "website/static/images/slack_icon.png",
]

# Add all PNGs from img/features/
features_dir = Path("website/static/img/features")
if features_dir.exists():
    TARGET_FILES += [str(p) for p in features_dir.glob("*.png")]


def convert_to_webp(png_path_str):
    png_path = Path(png_path_str)
    if not png_path.exists():
        return

    webp_path = png_path.with_suffix(".webp")
    try:
        img = Image.open(png_path).convert("RGBA")
        img.save(webp_path, "webp", quality=85, method=6)
    except Exception:
        pass  # Silent failure (CI-safe)


def main():
    for path in TARGET_FILES:
        convert_to_webp(path)


if __name__ == "__main__":
    main()
