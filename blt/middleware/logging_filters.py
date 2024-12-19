import logging
import threading

_thread_locals = threading.local()


def get_current_request():
    return getattr(_thread_locals, "request", None)


class ExcludeBlockedRequestsFilter(logging.Filter):
    def filter(self, record):
        request = get_current_request()
        if request:
            return not getattr(request, "blocked", False)
        return True
