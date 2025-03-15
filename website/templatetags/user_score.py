from django import template
from django.db.models import Sum

from website.models import Points

register = template.Library()


def score(value):
    return list(Points.objects.filter(user=value).aggregate(total_score=Sum("score")).values())[0]


register.filter("score", score)

