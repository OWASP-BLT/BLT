from django import forms
from django.test import TestCase, override_settings

from django_bleach import forms as bleach_forms
from testproject.forms import CustomBleachWidget
from testproject.models import Person

from .test_models import BleachContent


class BleachContentModelForm(forms.ModelForm):
    class Meta:
        model = BleachContent
        fields = "__all__"


class TestModelFormField(TestCase):
    def setUp(self):
        model_form = BleachContentModelForm()
        self.form_field = model_form.fields["content"]
        self.choice_form_field = model_form.fields["choice"]
        self.blank_field_form_field = model_form.fields["blank_field"]
        self.model_field = BleachContent()._meta.get_field("content")

    def test_formfield_type(self):
        """
        Check content's form field is instance of BleachField
        """
        self.assertIsInstance(self.form_field, bleach_forms.BleachField)

    def test_default_widget_type(self):
        """
        Widget class is Textarea when BLEACH_DEFAULT_WIDGET is not set.
        """
        form = forms.modelform_factory(Person, fields="__all__")()
        self.assertIsInstance(
            form.fields["biography"].widget,
            forms.Textarea,
        )

    @override_settings(
        BLEACH_DEFAULT_WIDGET="testproject.forms.CustomBleachWidget"
    )
    def test_custom_widget_type(self):
        """
        Widget class matches BLEACH_DEFAULT_WIDGET setting.
        """
        form = forms.modelform_factory(Person, fields="__all__")()
        self.assertIsInstance(
            form.fields["biography"].widget, CustomBleachWidget
        )

    @override_settings(
        BLEACH_DEFAULT_WIDGET="testproject.forms.CustomBleachWidget"
    )
    def test_widget_override(self):
        """
        Widget class matches widget class specified in overrides.
        """
        form = forms.modelform_factory(
            Person,
            fields="__all__",
            widgets={"biography": CustomBleachWidget},
        )()
        self.assertIsInstance(
            form.fields["biography"].widget, CustomBleachWidget
        )

    def test_same_allowed_args(self):
        """
        Check model and form's allowed arguments (tags, attributes, ...)
        are the same
        """
        form_allowed_args: dict = self.form_field.bleach_options
        model_allowed_args: dict = self.model_field.bleach_kwargs

        self.assertEqual(model_allowed_args, form_allowed_args)

    def test_with_choices(self):
        """
        Check if choices specified, use TextField's default widget (Select).
        """
        form_field_widget = self.choice_form_field.widget.__class__
        self.assertEqual(form_field_widget, forms.widgets.Select)

    def test_optional_field(self):
        """
        Check for the required flag on fields with `blank=True`
        """
        self.assertEqual(self.blank_field_form_field.required, False)

    def test_required_field(self):
        """
        Check for the required flag on fields
        """
        self.assertEqual(self.form_field.required, True)


class CustomBleachedFormField(bleach_forms.BleachField):
    ...


class OverriddenBleachContentModelForm(forms.ModelForm):
    class Meta:
        model = BleachContent
        fields = "__all__"
        field_classes = {
            "content": CustomBleachedFormField,
        }


class TestModelFormFieldOverrides(TestCase):
    def setUp(self):
        model_form = OverriddenBleachContentModelForm()
        self.form_field = model_form.fields["content"]

    def test_formfield_type(self):
        """
        Check content's form field is instance of CustomBleachedFormField.
        """
        self.assertIsInstance(self.form_field, CustomBleachedFormField)
