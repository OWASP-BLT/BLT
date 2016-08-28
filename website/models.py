from django.db import models
from django.contrib.auth.models import User

class Issue(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField()
    description = models.TextField()
    screenshot = models.ImageField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
