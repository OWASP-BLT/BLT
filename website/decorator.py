from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from website.models import Issue


def private_test_function(user, user_pk, issue_pk):
    try:
        issue = Issue.objects.get(id=issue_pk)
        if user.pk == user_pk and issue.user.pk == user.pk:
            return True

    except:
        return user.pk == user_pk


def private_access_check(
    message_to_deliver="Not allowed to \
            access the Private page",
):
    def decorator(view):
        @wraps(view)
        def _wrapped_view(request, *args, **kwargs):
            pk = kwargs.get("user_pk")
            issue_pk = kwargs.get("issue_pk")
            if not private_test_function(request.user, pk, issue_pk):
                messages.error(request, message_to_deliver)
                return redirect("/accounts/login")
            return view(request, *args, **kwargs)

        return _wrapped_view

    return decorator
