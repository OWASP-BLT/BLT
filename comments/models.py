from __future__ import unicode_literals
from website.models import Issue
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
# Create your models here.

class Comment(models.Model):
    issue = models.ForeignKey(Issue,on_delete=models.CASCADE,related_name='comments')
    author = models.CharField(max_length=200)
    author_url = models.CharField(max_length=200)
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.text
	
