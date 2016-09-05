from django import template
from website.models import  Points
from django.db.models import Sum

register = template.Library()


def score(value):
    return Points.objects.filter(user=value).aggregate(total_score=Sum('score')).values()[0]

register.filter('score', score)