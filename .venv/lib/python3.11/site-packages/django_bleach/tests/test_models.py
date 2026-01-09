from bleach.css_sanitizer import CSSSanitizer
from django.db import models
from django.test import TestCase
from django.utils.safestring import SafeString

from django_bleach.models import BleachField
from testproject.constants import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_CSS_PROPERTIES,
    ALLOWED_PROTOCOLS,
    ALLOWED_TAGS,
)


class BleachContent(models.Model):
    """Bleach test model"""

    CHOICES = (("f", "first choice"), ("s", "second choice"))
    content = BleachField(
        allowed_attributes=ALLOWED_ATTRIBUTES,
        allowed_protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSSSanitizer(
            allowed_css_properties=ALLOWED_CSS_PROPERTIES
        ),
        allowed_tags=ALLOWED_TAGS,
        allowed_styles=ALLOWED_CSS_PROPERTIES,
        strip_comments=True,
        strip_tags=True,
    )
    choice = BleachField(choices=CHOICES)
    blank_field = BleachField(blank=True)
    null_field = BleachField(blank=True, null=True)


class TestBleachModelField(TestCase):
    """Test model field"""

    def test_bleaching(self):
        """Test values are bleached"""
        test_data = {
            "no_tags": "<h1>Heading</h1>",
            "no_strip": "<h1>Heading</h1>",
            "bleach_strip": """<script>alert("Hello World")</script>""",
            "bleach_attrs": '<a href="http://www.google.com" '
            'target="_blank">google.com</a>',
            "bleach_css_sanitizer": '<li style="color: white">item</li>',
            "bleach_comment": "<!-- this is a comment -->",
        }
        expected_values = {
            "no_tags": "Heading",
            "no_strip": "Heading",
            "bleach_strip": """alert("Hello World")""",
            "bleach_attrs": "<a>google.com</a>",
            "bleach_css_sanitizer": '<li style="color: white;">item</li>',
            "bleach_comment": "",
        }

        for key, value in test_data.items():
            obj = BleachContent.objects.create(content=value)
            self.assertEqual(obj.content, expected_values[key])

    def test_retrieved_values_are_template_safe(self):
        obj = BleachContent.objects.create(content="some content")
        obj.refresh_from_db()
        self.assertIsInstance(obj.content, SafeString)
        obj = BleachContent.objects.create(content="")
        obj.refresh_from_db()
        self.assertIsInstance(obj.content, SafeString)

    def test_saved_values_are_template_safe(self):
        obj = BleachContent(content="some content")
        obj.save()
        self.assertIsInstance(obj.content, SafeString)
        obj = BleachContent(content="")
        obj.save()
        self.assertIsInstance(obj.content, SafeString)

    def test_saved_none_values_are_none(self):
        obj = BleachContent(null_field=None)
        obj.save()
        self.assertIsNone(obj.null_field)


class BleachNullableContent(models.Model):
    """Bleach test model"""

    content = BleachField(
        allowed_attributes=ALLOWED_ATTRIBUTES,
        allowed_protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSSSanitizer(
            allowed_css_properties=ALLOWED_CSS_PROPERTIES
        ),
        allowed_tags=ALLOWED_TAGS,
        strip_comments=True,
        strip_tags=True,
        blank=True,
        null=True,
    )


class TestBleachNullableModelField(TestCase):
    """Test model field"""

    def test_bleaching(self):
        """Test values are bleached"""
        test_data = {
            "none": None,
            "empty": "",
            "whitespaces": "   ",
            "linebreak": "\n",
        }
        expected_values = {
            "none": None,
            "empty": "",
            "whitespaces": "   ",
            "linebreak": "\n",
        }

        for key, value in test_data.items():
            obj = BleachNullableContent.objects.create(content=value)
            self.assertEqual(obj.content, expected_values[key])
