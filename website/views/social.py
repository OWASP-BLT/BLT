from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import render

from website.models import Queue


def queue_social_view(request):
    # Get all queue items ordered by creation date
    queue_items = Queue.objects.all().order_by("-created")

    # Add pagination - 10 items per page
    paginator = Paginator(queue_items, 10)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

        page_obj = paginator.page(1)

    return render(
        request,
        "social.html",
        {
            "queue_items": page_obj.object_list,
            "page_obj": page_obj,
        },
    )
