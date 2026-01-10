from decimal import Decimal
from django.test import TestCase
import random
from website.models import Project


class ProjectFreshnessFuzzTest(TestCase):
    def test_fuzz_freshness_bounds(self):
        """Fuzz test: freshness score must stay within 0-100 for random project states."""
        for i in range(100):
            p = Project.objects.create(
                name=f"FuzzProject{i}",
                slug=f"fuzz-project-{i}",
                description="Fuzz test project",
                status=random.choice(["flagship", "production", "incubator", "lab", "inactive"]),
                # Note: archived and forked fields may not exist in schema
                # Only include if they're actual model fields
            )
            score = p.calculate_freshness()
            self.assertGreaterEqual(score, Decimal("0.00"))
            self.assertLessEqual(score, Decimal("100.00"))
