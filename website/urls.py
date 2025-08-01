from django.urls import path
from website.views.core import home
from website.views.gemini import test_gemini, gemini_ui  # <-- use gemini_ui, not gemini_input_page

urlpatterns = [
    path('', home, name='home'),
    path('api/test-gemini/', test_gemini, name='test_gemini'),
    path('ask-gemini/', gemini_ui, name='gemini_ui'),
]
