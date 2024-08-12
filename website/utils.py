from django.db.models import Count
from .models import IP

def get_navigation_click_counts():
    click_counts = IP.objects.values('path').annotate(clicks=Count('path')).order_by('-clicks')
    return click_counts
