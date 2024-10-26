from django.urls import path
from . import views

urlpatterns = [
    path('daily_checkins/', views.daily_checkins, name='daily_checkins'),
    path('connect_to_slack/', views.connect_to_slack, name='connect_to_slack'),
]
