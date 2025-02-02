from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView

class CustomGitHubLoginView(OAuth2LoginView):
    adapter_class = GitHubOAuth2Adapter

    def get(self, request, *args, **kwargs):
        # Add custom logic before redirecting to GitHub
        print("Custom GitHub login initiated")
        return super().get(request, *args, **kwargs)