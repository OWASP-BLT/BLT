from django.urls import path
from . import views

urlpatterns = [
    # Example view
    path('team_overview', views.TeamOverview.as_view(), name='team_overview'),
    path('search-users/', views.search_users, name='search_users'),
    path('create-team/', views.create_team, name='create_team'),
    path('join-requests/', views.join_requests, name='join_requests'),
    path('add-member/', views.add_member, name='add_member'),
    path('delete-team/', views.delete_team, name='delete_team'),
    path('leave-team/', views.leave_team, name='leave_team'),
    path('challenges/', views.challenges, name='challenges'),
    path('update-progress/<int:challenge_id>/', views.update_progress, name='update_progress'),
]
