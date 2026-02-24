from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

from website.models import UserProfile

# Create your models here.


class Comment(models.Model):
    parent = models.ForeignKey("self", null=True, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Adding help_text to define the data contract for HTMX migration
    author = models.CharField(max_length=200, help_text="The name or username of the person posting the comment.")
    author_fk = models.ForeignKey(UserProfile, null=True, on_delete=models.SET_NULL)
    author_url = models.CharField(max_length=200)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        """Explicit return type; text truncated to 50 chars for UI stability."""
        return self.text[:50]

    def children(self) -> QuerySet:
        """Returns a QuerySet of child comments for threaded discussions."""
        return Comment.objects.filter(parent=self)
