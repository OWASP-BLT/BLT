from django.urls import path
from . import views

urlpatterns = [
    path('filter_contributions_by_year/<int:year>/', views.filter_contributions_by_year, name='filter_contributions_by_year'),
]
