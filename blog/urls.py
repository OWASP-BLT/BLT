from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

urlpatterns = [
    path("", views.PostListView.as_view(), name="blog"),
    path("new/", views.PostCreateView.as_view(), name="post_create"),
    path("<slug:slug>/", views.PostDetailView.as_view(), name="post_detail"),
    path("<slug:slug>/edit/", views.PostUpdateView.as_view(), name="post_update"),
    path("<slug:slug>/delete/", views.PostDeleteView.as_view(), name="post_delete"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
