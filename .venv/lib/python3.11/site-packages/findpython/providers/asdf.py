from __future__ import annotations

import os
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


class AsdfProvider(BaseProvider):
    """A provider that finds python installed with asdf"""

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def create(cls) -> Self | None:
        asdf_root = os.path.expanduser(
            os.path.expandvars(os.getenv("ASDF_DATA_DIR", "~/.asdf"))
        )
        if not os.path.exists(asdf_root):
            return None
        return cls(Path(asdf_root))

    def find_pythons(self) -> Iterable[PythonVersion]:
        python_dir = self.root / "installs/python"
        if not python_dir.exists():
            return
        for version in python_dir.iterdir():
            if version.is_dir():
                bindir = version / "bin"
                if not bindir.exists():
                    bindir = version
                yield from self.find_pythons_from_path(bindir, True)
