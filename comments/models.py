from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from website.models import Issue


# Create your models here.

class Comment(models.Model):
    parent = models.ForeignKey('self', null=True)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=200)
    author_url = models.CharField(max_length=200)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text

    def children(self):
        return Comment.objects.filter(parent=self)
