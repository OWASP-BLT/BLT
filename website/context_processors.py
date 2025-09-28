"""
Context processors for website app
"""
from django.db import models
from website.models import Tag


def popular_tags(request):
    """
    Add popular tags to all template contexts
    """
    try:
        # Get top 15 most used tags
        tags = Tag.objects.filter(is_active=True).annotate(
            usage_count=models.Count('organization', distinct=True) +
                       models.Count('issue', distinct=True) +
                       models.Count('courses', distinct=True) +
                       models.Count('lectures', distinct=True) +
                       models.Count('communities', distinct=True)
        ).filter(usage_count__gt=0).order_by('-usage_count')[:15]
        
        return {
            'global_popular_tags': tags,
        }
    except Exception:
        # In case of database errors during migrations, etc.
        return {
            'global_popular_tags': [],
        }