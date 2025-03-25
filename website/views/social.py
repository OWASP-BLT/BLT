from django.shortcuts import render

from website.models import Queue


def queue_social_view(request):
    # Get all queue items ordered by creation date
    queue_items = Queue.objects.all().order_by("-created")

    print("Queue items: ", queue_items[0].image)
    return render(request, "social.html", {"queue_items": queue_items})
