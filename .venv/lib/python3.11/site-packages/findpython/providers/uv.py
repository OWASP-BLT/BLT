from __future__ import annotations

import os
import typing as t
from pathlib import Path

import platformdirs

from findpython.providers.rye import RyeProvider


class UvProvider(RyeProvider):
    @classmethod
    def create(cls) -> t.Self | None:
        default_root_str = platformdirs.user_data_dir("uv", appauthor=False, roaming=True)
        root_str = os.getenv("UV_PYTHON_INSTALL_DIR")
        if root_str is None:
            root = Path(default_root_str).expanduser() / "python"
        else:
            root = Path(root_str).expanduser()
        return cls(root)
