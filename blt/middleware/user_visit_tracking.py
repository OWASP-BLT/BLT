class VisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # update visit counter for authenticated users who are not superusers
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                profile = request.user.userprofile
                profile.update_visit_counter()
            except Exception:
                pass

        response = self.get_response(request)
        return response

