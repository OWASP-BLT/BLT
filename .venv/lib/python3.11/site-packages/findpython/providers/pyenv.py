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


class PyenvProvider(BaseProvider):
    """A provider that finds python installed with pyenv"""

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def create(cls) -> Self | None:
        pyenv_root = os.path.expanduser(
            os.path.expandvars(os.getenv("PYENV_ROOT", "~/.pyenv"))
        )
        if not os.path.exists(pyenv_root):
            return None
        return cls(Path(pyenv_root))

    def find_pythons(self) -> Iterable[PythonVersion]:
        versions_path = self.root.joinpath("versions")
        if versions_path.exists():
            for version in versions_path.iterdir():
                if version.is_dir():
                    bindir = version / "bin"
                    if not bindir.exists():
                        bindir = version
                    yield from self.find_pythons_from_path(bindir, True)
