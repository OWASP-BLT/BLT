from django.urls import path
from .views import TimeLogListView, start_time_log

urlpatterns = [
    path('time-logs/', TimeLogListView.as_view(), name='time_logs'),
    path('start-time-log/', start_time_log, name='start_time_log'),
]
