from bleach import clean
from bleach.css_sanitizer import CSSSanitizer
from django.db import models
from django.utils.safestring import mark_safe

from . import forms
from .utils import get_bleach_default_options


class BleachField(models.TextField):
    def __init__(
        self,
        allowed_tags=None,
        allowed_attributes=None,
        allowed_styles=None,
        allowed_protocols=None,
        strip_tags=None,
        strip_comments=None,
        css_sanitizer=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.bleach_kwargs = get_bleach_default_options()

        if allowed_tags:
            self.bleach_kwargs["tags"] = allowed_tags
        if allowed_attributes:
            self.bleach_kwargs["attributes"] = allowed_attributes
        if allowed_styles:
            css_sanitizer = CSSSanitizer(allowed_css_properties=allowed_styles)
        if css_sanitizer:
            self.bleach_kwargs["css_sanitizer"] = css_sanitizer
        if allowed_protocols:
            self.bleach_kwargs["protocols"] = allowed_protocols
        if strip_tags:
            self.bleach_kwargs["strip"] = strip_tags
        if strip_comments:
            self.bleach_kwargs["strip_comments"] = strip_comments

    def formfield(self, form_class=forms.BleachField, **kwargs):
        """Makes the field for a ModelForm"""

        # If field doesn't have any choices add kwargs expected by BleachField.
        if not self.choices:
            kwargs.setdefault("widget", forms.get_default_widget())
            kwargs.update(
                {
                    "max_length": self.max_length,
                    "allowed_tags": self.bleach_kwargs.get("tags"),
                    "allowed_attributes": self.bleach_kwargs.get("attributes"),
                    "css_sanitizer": self.bleach_kwargs.get("css_sanitizer"),
                    "allowed_protocols": self.bleach_kwargs.get("protocols"),
                    "strip_tags": self.bleach_kwargs.get("strip"),
                    "strip_comments": self.bleach_kwargs.get("strip_comments"),
                    "required": not self.blank,
                }
            )

        return super().formfield(form_class=form_class, **kwargs)

    def pre_save(self, model_instance, add):
        data = getattr(model_instance, self.attname)
        if data is None:
            return data
        clean_value = clean(data, **self.bleach_kwargs) if data else ""
        setattr(model_instance, self.attname, mark_safe(clean_value))
        return clean_value

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        # Values are sanitised before saving, so any value returned from the DB
        # is safe to render unescaped.
        return mark_safe(value)
