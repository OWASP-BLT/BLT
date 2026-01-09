from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from findpython.providers.base import BaseProvider
from findpython.python import PythonVersion

if TYPE_CHECKING:
    import sys
    from typing import Iterable

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


@dataclass
class PathProvider(BaseProvider):
    """A provider that finds Python from PATH env."""

    paths: list[Path]

    @classmethod
    def create(cls) -> Self | None:
        paths = [Path(path) for path in os.getenv("PATH", "").split(os.pathsep) if path]
        return cls(paths)

    def find_pythons(self) -> Iterable[PythonVersion]:
        for path in self.paths:
            yield from self.find_pythons_from_path(path)
