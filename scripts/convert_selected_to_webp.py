import logging
from pathlib import Path

from PIL import Image

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# List of image paths to convert
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
        logger.warning(f"Not found: {png_path}")
        return

    webp_path = png_path.with_suffix(".webp")
    try:
        img = Image.open(png_path).convert("RGBA")
        img.save(webp_path, "webp", quality=85, method=6)
        logger.info(f"Converted: {png_path} → {webp_path}")
    except Exception as e:
        logger.error(f"Failed: {png_path} — {e}")


def main():
    for path in TARGET_FILES:
        convert_to_webp(path)


if __name__ == "__main__":
    main()
