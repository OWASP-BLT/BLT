from django.contrib import admin
try:
    from django.conf.urls import url, include
except ImportError:
    from django.urls import re_path as url, include
from tellme import urls


urlpatterns = [
    url('admin/', admin.site.urls),
    url('tellme/', include('tellme.urls')),
]
