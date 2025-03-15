import logging
import os

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from website.models import Queue
from website.utils import twitter

logger = logging.getLogger(__name__)


def queue_list(request):
    """
    Display a list of all queue items and handle all queue operations.
    This is a consolidated view that handles create, edit, delete, and launch operations.
    """
    # Check if user is authorized to view the page
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to access this page")
        return redirect("index")

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
                # Send tweet
                image_path = None
                if queue_item.image:
                    image_path = queue_item.image.path

                tweet_result = twitter.send_tweet(queue_item.message, image_path)

                if tweet_result["success"]:
                    # Update queue item with tweet information
                    queue_item.launched = True
                    queue_item.launched_at = timezone.now()
                    queue_item.txid = tweet_result["txid"]
                    queue_item.url = tweet_result["url"]
                    queue_item.save()

                    success_msg = (
                        f"Queue item launched successfully! "
                        f"Tweet posted at: <a href='{tweet_result['url']}' target='_blank'>{tweet_result['url']}</a> "
                        f"and sent to Discord and Slack #project-blt channels."
                    )
                    messages.success(request, success_msg)
                else:
                    # Still mark as launched but log the error
                    queue_item.launched = True
                    queue_item.launched_at = timezone.now()
                    queue_item.save()

                    logger.error(f"Error sending tweet: {tweet_result['error']}")
                    warning_msg = (
                        "Queue item marked as launched, but there was an error posting to Twitter. "
                        "The message was still sent to Discord and Slack #project-blt channels."
                    )
                    messages.warning(request, warning_msg)
            else:
                messages.info(request, "Queue item was already launched")

            return redirect("queue_list")

    # Check if user is authorized for launch control
    authorized_user_id = os.environ.get("Q_ID")
    is_auth = authorized_user_id and request.user.is_authenticated
    is_launch_authorized = is_auth and str(request.user.id) == authorized_user_id

    # Allow superusers to access the page
    is_superuser = request.user.is_superuser

    if not (is_launch_authorized or is_superuser):
        messages.error(request, "You are not authorized to access this page")
        return redirect("index")

    # Get pending and launched items for launch control section
    pending_items = Queue.objects.filter(launched=False).order_by("-created")
    launched_items = Queue.objects.filter(launched=True).order_by("-launched_at")[:10]

    context = {
        "queue_items": queue_items,
        "pending_items": pending_items,
        "launched_items": launched_items,
        "is_launch_authorized": is_launch_authorized or is_superuser,  # Allow superusers to launch
    }

    return render(request, "queue/list.html", context)


def update_txid(request, queue_id):
    """
    Update the txid and url for a queue item via HTMX.
    """
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    # Check if user is authorized for launch control
    authorized_user_id = os.environ.get("Q_ID")
    is_auth = authorized_user_id and request.user.is_authenticated
    is_launch_authorized = is_auth and str(request.user.id) == authorized_user_id
    is_superuser = request.user.is_superuser

    if not (is_launch_authorized or is_superuser):
        return HttpResponse("Unauthorized", status=401)

    if request.method == "POST":
        queue_item = get_object_or_404(Queue, id=queue_id)
        txid = request.POST.get("txid", "")
        url = request.POST.get("url", "")

        if txid:
            queue_item.txid = txid

        if url:
            queue_item.url = url

        queue_item.save()

        # Return the updated transaction details HTML
        context = {"item": queue_item}
        return render(request, "queue/partials/transaction_details.html", context)

    return HttpResponse("Method not allowed", status=405)

