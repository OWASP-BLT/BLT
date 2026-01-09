from django.template import Context, Template
from django.test import TestCase


class TestBleachTemplates(TestCase):
    """Test template tags"""

    def test_bleaching(self):
        """Test that unsafe tags are sanitised"""
        context = Context(
            {"some_unsafe_content": '<script>alert("Hello World!")</script>'},
        )
        template_to_render = Template(
            "{% load bleach_tags %}" "{{ some_unsafe_content|bleach }}"
        )
        rendered_template = template_to_render.render(context)
        self.assertInHTML(
            '&lt;script&gt;alert("Hello World!")&lt;/script&gt;',
            rendered_template,
        )

    def test_bleaching_none(self):
        """Test that None is handled properly as an input"""
        context = Context({"none_value": None})
        template_to_render = Template(
            "{% load bleach_tags %}" "{{ none_value|bleach }}"
        )
        rendered_template = template_to_render.render(context)
        self.assertEqual("None", rendered_template)

    def test_bleaching_tags(self):
        """Test provided tags are kept"""
        context = Context(
            {"some_unsafe_content": '<script>alert("Hello World!")</script>'}
        )
        template_to_render = Template(
            "{% load bleach_tags %}"
            '{{ some_unsafe_content|bleach:"script" }}'
        )
        rendered_template = template_to_render.render(context)
        self.assertInHTML(
            '<script>alert("Hello World!")</script>', rendered_template
        )

    def test_linkify(self):
        """Test bleach linkify"""
        url = "www.google.com"
        context = Context({"link_this": url})
        template_to_render = Template(
            "{% load bleach_tags %}" "{{ link_this|bleach_linkify|safe }}"
        )
        rendered_template = template_to_render.render(context)
        self.assertInHTML(
            '<a href="http://{0}" rel="nofollow">{0}</a>'.format(url),
            rendered_template,
        )

    def test_linkify_none(self):
        """Test bleach linkify with None as an input"""
        context = Context({"none_value": None})
        template_to_render = Template(
            "{% load bleach_tags %}" "{{ none_value|bleach_linkify }}"
        )
        rendered_template = template_to_render.render(context)
        self.assertEqual(
            "None",
            rendered_template,
        )
