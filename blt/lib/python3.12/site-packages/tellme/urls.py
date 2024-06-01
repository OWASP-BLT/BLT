import django

try:
    from django.urls import path, include
except ImportError:
    from django.conf.urls import url, include


from .views import get_feedback_screenshot, post_feedback


if django.VERSION[0] < 2:
    tellme_urlpatterns = [
        url(r'^post_feedback/$', post_feedback, name='post_feedback'),
        url(r'^get_feedback_screenshot/(?P<pk>\d+)/$', get_feedback_screenshot, name='get_feedback_screenshot'),
    ]

    urlpatterns = [
        url(r'^', include(tellme_urlpatterns,
            namespace='tellme')),
    ]
else:
    tellme_urlpatterns = [
        path('post_feedback/', post_feedback, name='post_feedback'),
        path('get_feedback_screenshot/<int:pk>/', get_feedback_screenshot, name='get_feedback_screenshot'),
    ]

    app_name = 'tellme'

    urlpatterns = [
        path('', include(tellme_urlpatterns,)),
    ]
