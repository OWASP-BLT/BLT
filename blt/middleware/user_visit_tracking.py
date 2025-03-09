class VisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # update visit counter for authenticated users
        if request.user.is_authenticated:
            try:
                profile = request.user.userprofile
                profile.update_visit_counter()
            except:
                pass

        response = self.get_response(request)
        return response
