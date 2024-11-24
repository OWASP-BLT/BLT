from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse


class Post(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to="blog_posts")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("post_detail", kwargs={"slug": self.slug})


@receiver(post_save, sender=Post)
def verify_file_upload(sender, instance, **kwargs):
    print("Verifying file upload...")
    if instance.image:
        print(f"Checking if image '{instance.image.name}' exists in the storage backend...")
        if not default_storage.exists(instance.image.name):
            print(f"Image '{instance.image.name}' was not uploaded to the storage backend.")
            raise ValidationError(
                f"Image '{instance.image.name}' was not uploaded to the storage backend."
            )
