import logging
import os

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from website.models import Queue

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

            # Get current time
            current_time = timezone.now()

            # Check if this is the first launch
            was_unlaunched = not queue_item.launched

            if was_unlaunched:
                # Mark as launched
                queue_item.launch(current_time)
                
                # Create Twitter intent URL
                base_url = "https://twitter.com/intent/tweet"
                params = {
                    "text": queue_item.message,
                }
                
                # Build the final URL
                tweet_url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
                
                # Redirect directly to Twitter in a new tab
                response = redirect(tweet_url)
                response['X-Frame-Options'] = 'ALLOW-FROM https://twitter.com'
                return response
            else:
                # Just update the timestamp if already launched
                queue_item.launch(current_time)
                messages.info(
                    request,
                    f"Queue item was already launched. Launch timestamp updated to {current_time.strftime('%Y-%m-%d %H:%M:%S')}.",
                )
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
        txid = request.POST.get("txid", "").strip()
        url = request.POST.get("url", "").strip()

        # Track what was updated for the message
        txid_updated = False
        url_updated = False
        txid_removed = False
        url_removed = False

        # Only update txid if provided, otherwise keep existing value
        if txid and txid != queue_item.txid:
            queue_item.txid = txid
            txid_updated = True

        # Only update url if provided, otherwise keep existing value
        if url and url != queue_item.url:
            queue_item.url = url
            url_updated = True

        # Clear values if explicitly submitted as empty
        if "txid" in request.POST and not txid and queue_item.txid:
            queue_item.txid = None
            txid_removed = True

        if "url" in request.POST and not url and queue_item.url:
            queue_item.url = None
            url_removed = True

        queue_item.save()

        # Build the response message
        message_parts = []
        if txid_updated:
            message_parts.append("Transaction ID updated")
        if url_updated:
            message_parts.append("URL updated")
        if txid_removed:
            message_parts.append("Transaction ID removed")
        if url_removed:
            message_parts.append("URL removed")

        # Create the appropriate message
        if message_parts:
            message = f"Success: {' and '.join(message_parts)}"
        else:
            message = "No changes were made"

        # Check which target is being updated based on the HTTP_HX_TARGET header
        hx_target = request.META.get("HTTP_HX_TARGET", "")

        context = {"item": queue_item, "message": message}

        # Determine which template to use based on the target ID
        if "launch-transaction-details" in hx_target:
            # This is for the launch control section
            return render(request, "queue/partials/launch_transaction_details.html", context)
        else:
            # This is for the main list section
            return render(request, "queue/partials/transaction_details.html", context)

    return HttpResponse("Method not allowed", status=405)
