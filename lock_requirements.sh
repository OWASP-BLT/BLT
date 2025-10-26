#!/usr/bin/env bash

set -euo pipefail

echo "Generating requirements lock files using uv (manual use only)."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Please install uv first: https://docs.astral.sh/uv/"
  exit 1
fi

# Ensure we run from the script's directory (project root expected)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "pyproject.toml" ]; then
  echo "pyproject.toml not found in current directory. Run this script from the project root."
  exit 1
fi

echo "Creating requirements.txt (default groups only, frozen, no hashes)..."
uv export \
  --frozen \
  --no-hashes \
  --no-emit-project \
  --output-file=requirements.txt

echo "Creating requirements-dev.txt (all groups, frozen, no hashes)..."
uv export \
  --frozen \
  --no-hashes \
  --no-emit-project \
  --all-groups \
  --output-file=requirements-dev.txt

echo "Done. Generated files: requirements.txt, requirements-dev.txt"


