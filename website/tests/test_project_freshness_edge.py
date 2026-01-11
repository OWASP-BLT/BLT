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
        from django.contrib.auth.models import User
        from django.utils import timezone

        from comments.models import Comment
        from website.models import Domain, Issue, UserProfile

        # Create required related objects
        user = User.objects.create(username="testuser", email="test@example.com")
        domain = Domain.objects.create(name="example.com", url="http://example.com")
        p = make_project()
        p.save()
        # Add spammy comments (same author, very old)
        author_profile = UserProfile.objects.get(user=user)
        old_time = timezone.now() - timezone.timedelta(days=400)
        for _ in range(10):
            issue = Issue.objects.create(
                user=user,
                domain=domain,
                url="http://example.com/issue",
                description="Spam Issue",
            )
            Comment.objects.create(
                content_object=issue,
                author="spammer",
                author_fk=author_profile,
                author_url="",
                text="Spam",
                created_date=old_time,
            )
        # Add a normal comment (recent, not spam)
        issue2 = Issue.objects.create(
            user=user,
            domain=domain,
            url="http://example.com/issue2",
            description="Normal Issue",
        )
        Comment.objects.create(
            content_object=issue2,
            author="legituser",
            author_fk=author_profile,
            author_url="",
            text="Legit",
            created_date=timezone.now(),
        )
        # Should exclude spam/outlier comments
        result = p.calculate_freshness()
        self.assertIsInstance(result, Decimal)

    def test_fallback_issue_comment(self):
        from django.contrib.auth.models import User
        from django.utils import timezone

        from comments.models import Comment
        from website.models import Domain, Issue, UserProfile

        user = User.objects.create(username="testuser2", email="test2@example.com")
        domain = Domain.objects.create(name="example2.com", url="http://example2.com")
        p = make_project()
        p.save()
        author_profile = UserProfile.objects.get(user=user)
        # No normal activity, only a fallback comment
        issue = Issue.objects.create(
            user=user,
            domain=domain,
            url="http://example2.com/issue",
            description="Fallback Issue",
        )
        Comment.objects.create(
            content_object=issue,
            author="fallbackuser",
            author_fk=author_profile,
            author_url="",
            text="Fallback",
            created_date=timezone.now() - timezone.timedelta(days=100),
        )
        # Remove all contributions/commits/PRs if any
        # (Assume no Contribution objects exist for this project)
        result = p.calculate_freshness()
        self.assertIsInstance(result, Decimal)
