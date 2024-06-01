"""Package settings."""
import functools
from typing import Any, Dict, Optional, Tuple

from django.conf import settings as django_settings

try:
    from pydantic import Field, validator
    from pydantic.env_settings import BaseSettings, SettingsSourceCallable
except:  # pragma: no cover
    from pydantic.v1.env_settings import BaseSettings, SettingsSourceCallable  # type: ignore
    from pydantic.v1 import Field, validator  # type: ignore

from .schemas import WidgetOptions, WidgetVariant


def _django_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    return getattr(django_settings, "BOOTSTRAP_DATEPICKER_PLUS", {})


class WidgetSettings(BaseSettings):
    """Settings to customize input widgets."""

    template_name: Optional[str]
    attrs: Dict[str, str] = {}
    options: WidgetOptions = {}
    variant_options: Dict[WidgetVariant, WidgetOptions] = {}
    addon_icon_classes: Dict[WidgetVariant, str] = {
        WidgetVariant.date: "bi-calendar",
        WidgetVariant.time: "bi-clock",
        WidgetVariant.datetime: "bi-calendar",
        WidgetVariant.month: "bi-calendar",
        WidgetVariant.year: "bi-calendar",
    }
    momentjs_url: Optional[
        str
    ] = "https://cdn.jsdelivr.net/npm/moment@2.29.4/min/moment-with-locales.min.js"
    datetimepicker_js_url: Optional[
        str
    ] = "https://cdn.jsdelivr.net/npm/eonasdan-bootstrap-datetimepicker@4.17.49/build/js/bootstrap-datetimepicker.min.js"
    datetimepicker_css_url: Optional[
        str
    ] = "https://cdn.jsdelivr.net/npm/eonasdan-bootstrap-datetimepicker@4.17.49/build/css/bootstrap-datetimepicker.min.css"
    bootstrap_icon_css_url: Optional[
        str
    ] = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.9.1/font/bootstrap-icons.css"
    app_static_url = "https://cdn.jsdelivr.net/gh/monim67/django-bootstrap-datepicker-plus@5.0.2/src/bootstrap_datepicker_plus/static/bootstrap_datepicker_plus/"
    debug: bool = Field(default_factory=lambda: getattr(django_settings, "DEBUG", True))

    @validator("addon_icon_classes")
    def _merge_with_default_dict_value(cls, v, field):  # type: ignore
        return {**field.default, **v}

    class Config:
        """Customize pydantic config."""

        env_prefix = "BOOTSTRAP_DATEPICKER_PLUS_"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            """Add django settings as config source."""
            return (
                init_settings,
                env_settings,
                file_secret_settings,
                _django_settings_source,
            )


@functools.lru_cache(maxsize=1)
def get_widget_settings() -> WidgetSettings:
    """Initialize and return WidgetSettings."""
    return WidgetSettings()
