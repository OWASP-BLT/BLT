from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from website.models import UserProfile

# Create your models here.


class Comment(models.Model):
    parent = models.ForeignKey("self", null=True, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    author = models.CharField(max_length=200)
    author_fk = models.ForeignKey(UserProfile, null=True, on_delete=models.SET_NULL)
    author_url = models.CharField(max_length=200)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text

    def children(self):
        return Comment.objects.filter(parent=self)

