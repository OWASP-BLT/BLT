from typing import Optional

from pydantic import BaseModel, Field

from .schemas import WidgetOptions, WidgetVariant


class WidgetConfig(BaseModel):
    """Widget config which is passed to input on render."""

    variant: WidgetVariant
    backend_date_format: str
    options: WidgetOptions = Field(default_factory=dict)
    range_from: Optional[str]

    def update_options(self, *options_args: Optional[WidgetOptions]) -> None:
        """Update options merging WidgetOptions sequentially."""
        for options_arg in options_args:
            if options_arg is not None:
                self.options.update(options_arg)

    def to_attr_value(self) -> str:
        """Convert to attr string value."""
        return self.json(exclude_none=True)
