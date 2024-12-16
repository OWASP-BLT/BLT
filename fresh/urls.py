from django.urls import path
from . import views

urlpatterns = [
    # Example view
    path('team_overview', views.TeamOverview.as_view(), name='team_overview'),
    path('search-users/', views.search_users, name='search_users'),
    path('create-team/', views.create_team, name='create_team'),
]
