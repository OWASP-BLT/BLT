import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from comments.models import Comment
from website.models import Issue, UserActivity

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Issue)
def log_bug_report(sender, instance, created, **kwargs):
    """Log bug report activity when a new issue is created."""
    if not created or not instance.user:  # user check
        return

    try:
        # Extract organization from domain if available
        organization = None
        if instance.domain and hasattr(instance.domain, "organization"):
            organization = instance.domain.organization

        # Create activity record
        UserActivity.objects.create(
            user=instance.user,
            organization=organization,
            activity_type="bug_report",
            metadata={
                "issue_id": instance.id,
                # Always record the human-readable label, including "General" (0)
                "label": instance.get_label_display(),
            },
        )
    except Exception as e:
        logger.error("Failed to log bug report activity: %s", str(e), exc_info=True)


@receiver(post_save, sender=Comment)  # ✓ Changed from IssueComment to Comment
def log_bug_comment(sender, instance, created, **kwargs):
    """Log bug comment activity when a new comment is created on an Issue."""
    if not created:
        return

    try:
        # ✓ Only track comments on Issues (not other content types)
        issue_content_type = ContentType.objects.get_for_model(Issue)
        if instance.content_type != issue_content_type:
            return

        # ✓ Get the user from author_fk -> userprofile -> user
        if not instance.author_fk or not hasattr(instance.author_fk, "user"):
            return

        user = instance.author_fk.user

        # ✓ Get the Issue object using content_type and object_id
        try:
            issue = Issue.objects.get(pk=instance.object_id)
        except Issue.DoesNotExist:
            return

        # Extract organization from issue domain if available
        organization = None
        if issue.domain and hasattr(issue.domain, "organization"):
            organization = issue.domain.organization

        # Create activity record
        UserActivity.objects.create(
            user=user,
            organization=organization,
            activity_type="bug_comment",
            metadata={
                "comment_id": instance.id,
                "issue_id": issue.id,
            },
        )
    except Exception as e:
        logger.error("Failed to log bug report activity: %s", str(e), exc_info=True)
