from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from findpython.providers.base import BaseProvider
from findpython.python import PythonVersion
from findpython.utils import WINDOWS, safe_iter_dir

if TYPE_CHECKING:
    import sys
    from typing import Iterable

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class RyeProvider(BaseProvider):
    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def create(cls) -> Self | None:
        root = Path(os.getenv("RYE_PY_ROOT", "~/.rye/py")).expanduser()
        return cls(root)

    def find_pythons(self) -> Iterable[PythonVersion]:
        if not self.root.exists():
            return
        for child in safe_iter_dir(self.root):
            for intermediate in ("", "install/"):
                if WINDOWS:
                    python_bin = child / (intermediate + "python.exe")
                else:
                    python_bin = child / (intermediate + "bin/python3")
                if python_bin.exists():
                    yield self.version_maker(python_bin, _interpreter=python_bin)
                    break
