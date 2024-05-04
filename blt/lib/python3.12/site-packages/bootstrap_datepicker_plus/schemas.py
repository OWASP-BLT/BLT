"""Datastructures of the package."""

from enum import Enum
from typing import Any, Dict, Union

from typing_extensions import TypeAlias

InputAttrs: TypeAlias = Dict[str, Any]
WidgetOptions: TypeAlias = Dict[str, Union[bool, int, str, Dict[str, str]]]


class WidgetVariant(str, Enum):
    """Variants of widgets."""

    date = "date"
    time = "time"
    datetime = "datetime"
    month = "month"
    year = "year"
