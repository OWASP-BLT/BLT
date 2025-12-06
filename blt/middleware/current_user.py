from website.views.security_incident_signals import set_current_user


class CurrentUserMiddleware:
    """
    Store current request.user in thread-local storage so signals can access it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if request.user.is_authenticated:
                set_current_user(request.user)
            else:
                set_current_user(None)

            return self.get_response(request)
        finally:
            # Clean up thread-local storage after request
            set_current_user(None)
