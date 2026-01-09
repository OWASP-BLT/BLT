from __future__ import annotations

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


class MacOSProvider(BaseProvider):
    """A provider that finds python from macos typical install base
    with python.org installer.
    """

    INSTALL_BASE = Path("/Library/Frameworks/Python.framework/Versions/")

    @classmethod
    def create(cls) -> Self | None:
        if not cls.INSTALL_BASE.exists():
            return None
        return cls()

    def find_pythons(self) -> Iterable[PythonVersion]:
        for version in self.INSTALL_BASE.iterdir():
            if version.is_dir():
                yield from self.find_pythons_from_path(version / "bin", True)
