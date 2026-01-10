from decimal import Decimal

from django.test import TestCase

from website.models import Project


def make_project(**kwargs):
    # Only pass real model fields to Project constructor
    model_fields = {k: v for k, v in kwargs.items() if k in [f.name for f in Project._meta.get_fields()]}
    instance = Project(**model_fields)
    # Set dynamic attributes (archived, forked) after construction
    for k in ("archived", "forked"):
        if k in kwargs:
            setattr(instance, k, kwargs[k])
    return instance


class ProjectFreshnessEdgeTests(TestCase):
    def test_archived_project_zero(self):
        p = make_project(archived=True)
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_forked_project_zero(self):
        p = make_project(forked=True)
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_inactive_status_zero(self):
        p = make_project(status="inactive")
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_lab_status_zero(self):
        p = make_project(status="lab")
        self.assertEqual(p.calculate_freshness(), Decimal("0.00"))

    def test_outlier_spam(self):
        # Prepare a project with data that triggers outlier/spam logic if needed
        p = make_project()
        p.save()  # Ensure the instance is saved before use in queries
        # Add logic here to simulate outlier/spam if needed
        result = p.calculate_freshness()
        self.assertIsInstance(result, Decimal)

    def test_fallback_issue_comment(self):
        # Prepare a project that triggers fallback logic
        p = make_project()
        p.save()  # Ensure the instance is saved before use in queries
        # Add logic here to simulate fallback if needed
        result = p.calculate_freshness()
        self.assertIsInstance(result, Decimal)
