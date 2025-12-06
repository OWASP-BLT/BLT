import logging

logger = logging.getLogger(__name__)


class VisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # update visit counter for authenticated users who are not superusers
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                profile = request.user.userprofile
                profile.update_visit_counter()
            except Exception as e:
                # Log the exception to help with debugging
                logger.debug("Failed to update visit counter: %s", type(e).__name__)
                # Silently ignore any errors to prevent middleware from breaking requests
                # This includes TransactionManagementError during test teardown
                pass

        response = self.get_response(request)
        return response
