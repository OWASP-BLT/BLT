import os

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from website.models import Queue


def queue_list(request):
    """
    Display a list of all queue items and handle all queue operations.
    This is a consolidated view that handles create, edit, delete, and launch operations.
    """
    queue_items = Queue.objects.all().order_by("-created")

    # Handle create operation
    if request.method == "POST" and "action" in request.POST:
        action = request.POST.get("action")

        # Create new queue item
        if action == "create":
            message = request.POST.get("message", "")
            image = request.FILES.get("image")

            if not message:
                messages.error(request, "Message is required")
                return redirect("queue_list")

            if len(message) > 140:
                messages.error(request, "Message must be 140 characters or less")
                return redirect("queue_list")

            queue_item = Queue(message=message, image=image)
            queue_item.save()

            messages.success(request, "Queue item created successfully")
            return redirect("queue_list")

        # Edit existing queue item
        elif action == "edit":
            queue_id = request.POST.get("queue_id")
            queue_item = get_object_or_404(Queue, id=queue_id)

            message = request.POST.get("message", "")
            image = request.FILES.get("image")

            if not message:
                messages.error(request, "Message is required")
                return redirect("queue_list")

            if len(message) > 140:
                messages.error(request, "Message must be 140 characters or less")
                return redirect("queue_list")

            queue_item.message = message
            if image:
                queue_item.image = image
            queue_item.save()

            messages.success(request, "Queue item updated successfully")
            return redirect("queue_list")

        # Delete queue item
        elif action == "delete":
            queue_id = request.POST.get("queue_id")
            queue_item = get_object_or_404(Queue, id=queue_id)
            queue_item.delete()

            messages.success(request, "Queue item deleted successfully")
            return redirect("queue_list")

        # Launch queue item
        elif action == "launch":
            queue_id = request.POST.get("queue_id")
            queue_item = get_object_or_404(Queue, id=queue_id)

            if not queue_item.launched:
                queue_item.launched = True
                queue_item.launched_at = timezone.now()
                queue_item.save()
                messages.success(request, "Queue item launched successfully")
            else:
                messages.info(request, "Queue item was already launched")

            return redirect("queue_list")

    # Check if user is authorized for launch control
    authorized_user_id = os.environ.get("Q_ID")
    is_auth = authorized_user_id and request.user.is_authenticated
    is_launch_authorized = is_auth and str(request.user.id) == authorized_user_id

    # Get pending and launched items for launch control section
    pending_items = Queue.objects.filter(launched=False).order_by("-created")
    launched_items = Queue.objects.filter(launched=True).order_by("-launched_at")[:10]

    context = {
        "queue_items": queue_items,
        "pending_items": pending_items,
        "launched_items": launched_items,
        "is_launch_authorized": is_launch_authorized,
    }

    return render(request, "queue/list.html", context)
