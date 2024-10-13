from django.urls import path
from . import views

urlpatterns = [
    path('mark_duplicate/', views.mark_duplicate, name='mark_duplicate'),
    path('approve_duplicate/', views.approve_duplicate, name='approve_duplicate'),
    path('validate_issue/', views.validate_issue, name='validate_issue'),
]
