import hashlib
import hmac
import json
import os
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from slack import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

DEPLOYS_CHANNEL_NAME = "#project-blt-lettuce-deploys"
JOINS_CHANNEL_ID = "C076DAG65AT"
CONTRIBUTE_ID = "C077QBBLY1Z"

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SIGNING_SECRET = os.getenv("SIGNING_SECRET")
client = WebClient(token=SLACK_TOKEN)


def verify_slack_signature(request):
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Verify timestamp to prevent replay attacks
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{request.body.decode()}"
    my_signature = (
        "v0="
        + hmac.new(SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    )

    return hmac.compare_digest(my_signature, signature)


@csrf_exempt
def slack_events(request):
    """Handle incoming Slack events"""
    if request.method == "POST":
        # Verify the request is from Slack
        if not verify_slack_signature(request):
            return HttpResponse(status=403)

        data = json.loads(request.body)

        if "challenge" in data:
            return JsonResponse({"challenge": data["challenge"]})

        event = data.get("event", {})
        event_type = event.get("type")

        if event_type == "team_join":
            user_data = event.get("user", {})
            if isinstance(user_data, dict):
                user_id = user_data.get("id")
            else:
                user_id = event.get("user")

            if user_id:
                _handle_team_join(user_id)

        elif event_type == "message":
            handle_message(event)

        return HttpResponse(status=200)
    return HttpResponse(status=405)


def extract_text_from_blocks(blocks):
    """Extracts message text from Slack's 'blocks' format"""
    if not blocks:
        return ""

    text_parts = []
    for block in blocks:
        if block.get("type") == "rich_text":
            for element in block.get("elements", []):
                if element.get("type") == "rich_text_section":
                    for item in element.get("elements", []):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))

    return " ".join(text_parts).strip()


def _handle_contribute_message(message):
    text = message.get("text", "").lower()
    user = message.get("user")
    channel = message.get("channel")

    if message.get("subtype") is None and any(
        keyword in text for keyword in ["contribute", "contributing", "contributes"]
    ):
        response = client.chat_postMessage(
            channel=channel,
            text=f"Hello <@{user}>! Please check <#{CONTRIBUTE_ID}> for contributing guidelines today!",
        )


def _handle_team_join(user_id):
    # Send message to joins channel
    join_response = client.chat_postMessage(
        channel=JOINS_CHANNEL_ID, text=f"Welcome <@{user_id}> to the team! 🎉"
    )

    try:
        # Try to open DM first
        dm_response = client.conversations_open(users=[user_id])
        if not dm_response["ok"]:
            return

        dm_channel = dm_response["channel"]["id"]

        # Define welcome message
        welcome_message = (
            f":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
            "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
            "this Slack workspace is the perfect place to connect, collaborate, and stay informed about all things OWASP.\n\n"
            ":small_blue_diamond: *Get Involved:*\n"
            "• Check out the *#contribute* channel to find ways to get involved with OWASP projects and initiatives.\n"
            "• Explore individual project channels, which are named *#project-name*, to dive into specific projects that interest you.\n"
            "• Join our chapter channels, named *#chapter-name*, to connect with local OWASP members in your area.\n\n"
            ":small_blue_diamond: *Stay Updated:*\n"
            "• Visit *#newsroom* for the latest updates and announcements.\n"
            "• Follow *#external-activities* for news about OWASP's engagement with the wider security community.\n\n"
            ":small_blue_diamond: *Connect and Learn:*\n"
            "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
            "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
            "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
            "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
            "• *#github-admins*: Get support and discuss issues related to OWASP's GitHub repositories.\n"
            "• *#learning*: Share and find resources to expand your knowledge in the field of application security.\n\n"
            "We're excited to see the amazing contributions you'll make. If you have any questions or need assistance, don't hesitate to ask. "
            "Let's work together to make software security visible and improve the security of the software we all rely on.\n\n"
            "Welcome aboard! :rocket:"
        )

        welcome_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": welcome_message}}]

        welcome_response = client.chat_postMessage(
            channel=dm_channel, text=welcome_message, blocks=welcome_blocks
        )

    except SlackApiError as e:
        return HttpResponse(status=500)


def handle_message(payload):
    # Get bot user ID
    response = client.auth_test()
    bot_user_id = response["user_id"]

    # Skip if message is from the bot
    if payload.get("user") == bot_user_id:
        return

    # Get message content from both text and blocks
    text = payload.get("text", "")
    blocks_text = extract_text_from_blocks(payload.get("blocks", []))

    # Use text from blocks if direct text is empty
    message_text = text or blocks_text

    # Create message object with the extracted text
    message = {
        "user": payload.get("user"),
        "channel": payload.get("channel"),
        "text": message_text,
        "subtype": payload.get("subtype"),
        "channel_type": payload.get("channel_type"),
    }

    _handle_contribute_message(message)
    _handle_direct_message(message, bot_user_id)


def _handle_direct_message(message, bot_user_id):
    if message.get("channel_type") == "im":
        user = message["user"]
        text = message.get("text", "")

        try:
            if message.get("user") != bot_user_id:
                client.chat_postMessage(channel=JOINS_CHANNEL_ID, text=f"<@{user}> said {text}")
            client.chat_postMessage(channel=user, text=f"Hello <@{user}>, you said: {text}")
        except SlackApiError as e:
            return HttpResponse(status=500)
