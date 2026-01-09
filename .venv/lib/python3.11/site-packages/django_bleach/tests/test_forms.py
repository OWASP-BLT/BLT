from bleach.css_sanitizer import CSSSanitizer
from django import forms
from django.test import TestCase, override_settings
from django.utils.safestring import SafeString

from django_bleach.forms import BleachField
from testproject.constants import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_CSS_PROPERTIES,
    ALLOWED_PROTOCOLS,
    ALLOWED_STYLES,
    ALLOWED_TAGS,
)
from testproject.forms import BleachForm, CustomBleachWidget


class TestBleachField(TestCase):
    def test_empty(self):
        """
        Test that the empty_value arg is returned for any input empty value
        """
        for requested_empty_value in ("", None):
            field = BleachField(empty_value=requested_empty_value)
            for empty_value in field.empty_values:
                self.assertEqual(
                    field.to_python(empty_value), requested_empty_value
                )

    def test_return_type(self):
        """Test bleached values are SafeString objects"""
        field = BleachField()
        self.assertIsInstance(field.to_python("some text"), SafeString)

    def test_bleaching(self):
        """Test values are bleached"""
        test_data = {
            "no_tags": "<h1>Heading</h1>",
            "no_strip": "<h1>Heading</h1>",
            "bleach_strip": "<!-- script here -->"
            '<script>alert("Hello World")</script>',
            "bleach_attrs": '<a href="https://www.google.com" '
            'target="_blank">google.com</a>',
            "bleach_css_sanitizer": '<li style="color: white">item</li>',
        }
        form = BleachForm(data=test_data)
        form.is_valid()
        self.assertEqual(form.cleaned_data["no_tags"], "Heading")
        self.assertEqual(
            form.cleaned_data["no_strip"], "&lt;h1&gt;Heading&lt;/h1&gt;"
        )
        self.assertEqual(
            form.cleaned_data["bleach_strip"], 'alert("Hello World")'
        )
        self.assertEqual(
            form.cleaned_data["bleach_attrs"],
            '<a href="https://www.google.com">google.com</a>',
        )
        self.assertNotEqual(
            form.cleaned_data["bleach_css_sanitizer"],
            test_data["bleach_css_sanitizer"],
        )

    def test_tags(self):
        """Test allowed tags are rendered"""
        test_data = {
            "no_tags": "<p>No tags here</p>",
            "no_strip": "No tags here",
            "bleach_strip": "<ul><li>one</li><li>two</li></ul>",
            "bleach_attrs": '<a href="https://www.google.com" '
            'title="Google">google.com</a>',
            "bleach_css_sanitizer": '<li style="color: white;">item</li>',
        }
        form = BleachForm(data=test_data)
        form.is_valid()
        self.assertEqual(form.cleaned_data["no_tags"], "No tags here")
        self.assertEqual(form.cleaned_data["no_strip"], "No tags here")

        self.assertEqual(
            form.cleaned_data["bleach_strip"], test_data["bleach_strip"]
        )
        self.assertEqual(
            form.cleaned_data["bleach_attrs"], test_data["bleach_attrs"]
        )
        self.assertEqual(
            form.cleaned_data["bleach_css_sanitizer"],
            test_data["bleach_css_sanitizer"],
        )

    def test_attrs(self):
        """Test allowed attributes are rendered"""
        list_html = (
            '<ul class="our-list">'
            '<li class="list-item">one</li>'
            "<li>two</li>"
            "</ul>"
        )
        test_data = {
            "no_strip": "",
            "no_tags": list_html,
            "bleach_strip": list_html,
            "bleach_attrs": list_html,
            "bleach_css_sanitizer": list_html,
        }
        form = BleachForm(data=test_data)
        form.is_valid()
        self.assertEqual(form.cleaned_data["no_tags"], "\none\ntwo")

        self.assertEqual(
            form.cleaned_data["bleach_strip"],
            "<ul><li>one</li><li>two</li></ul>",
        )
        self.assertEqual(
            form.cleaned_data["bleach_attrs"], test_data["bleach_strip"]
        )
        self.assertEqual(
            form.cleaned_data["bleach_css_sanitizer"],
            "<ul><li>one</li><li>two</li></ul>",
        )


@override_settings(
    BLEACH_DEFAULT_WIDGET="testproject.forms.CustomBleachWidget"
)
class TestCustomWidget(TestCase):
    def setUp(self):
        class CustomForm(forms.Form):
            # Define form inside function with overridden settings so
            # get_default_widget() sees the modified setting.
            no_tags = BleachField(
                max_length=100, strip_tags=True, allowed_tags=[]
            )
            no_strip = BleachField(
                max_length=100, allowed_tags=None, allowed_attributes=None
            )
            bleach_strip = BleachField(
                max_length=100,
                strip_comments=True,
                strip_tags=True,
                allowed_tags=ALLOWED_TAGS,
            )
            bleach_attrs = BleachField(
                max_length=100,
                strip_tags=False,
                allowed_tags=ALLOWED_TAGS,
                allowed_protocols=ALLOWED_PROTOCOLS,
                allowed_attributes=ALLOWED_ATTRIBUTES,
            )
            bleach_styles = BleachField(
                max_length=100,
                strip_tags=False,
                allowed_attributes=["style"],
                allowed_tags=ALLOWED_TAGS,
                allowed_styles=ALLOWED_STYLES,
            )
            bleach_css_sanitizer = BleachField(
                max_length=100,
                strip_tags=False,
                allowed_attributes=["style"],
                allowed_tags=ALLOWED_TAGS,
                css_sanitizer=CSSSanitizer(
                    allowed_css_properties=ALLOWED_CSS_PROPERTIES
                ),
            )

        self.CustomForm = CustomForm

    def test_custom_widget_type(self):
        """Test widget class matches BLEACH_DEFAULT_WIDGET"""
        for field in self.CustomForm().fields.values():
            self.assertIsInstance(field.widget, CustomBleachWidget)

    def test_custom_widget_bleaches_content(self):
        """
        Test input is bleached according to config while using a custom
        widget
        """
        test_data = {
            "no_tags": "<h1>Heading</h1>",
            "no_strip": "<h1>Heading</h1>",
            "bleach_strip": "<!-- script here -->"
            '<script>alert("Hello World")</script>',
            "bleach_attrs": (
                '<a href="http://www.google.com" '
                'target="_blank">google.com</a>'
                '<a href="https://www.google.com">google.com</a>'
            ),
            "bleach_styles": '<li style="color: white">item</li>',
            "bleach_css_sanitizer": '<li style="color: white">item</li>',
        }
        form = self.CustomForm(data=test_data)
        form.is_valid()
        self.assertEqual(form.cleaned_data["no_tags"], "Heading")
        self.assertEqual(
            form.cleaned_data["no_strip"], "&lt;h1&gt;Heading&lt;/h1&gt;"
        )
        self.assertEqual(
            form.cleaned_data["bleach_strip"], 'alert("Hello World")'
        )
        self.assertEqual(
            form.cleaned_data["bleach_attrs"],
            '<a>google.com</a><a href="https://www.google.com">google.com</a>',
        )
        self.assertNotEqual(
            form.cleaned_data["bleach_styles"], test_data["bleach_styles"]
        )
        self.assertNotEqual(
            form.cleaned_data["bleach_css_sanitizer"],
            test_data["bleach_css_sanitizer"],
        )
