import json

import requests
from django.conf import settings
from django.http import JsonResponse

from blt import settings
from website.models import BaconEarning


# @login_required
def batch_send_bacon_tokens_view(request):
    # Get all users with non-zero tokens_earned
    users_with_tokens = BaconEarning.objects.filter(tokens_earned__gt=0)

    if not users_with_tokens.exists():
        return JsonResponse({"status": "error", "message": "No eligible users with tokens to send."})

    # Build YAML content
    yaml_outputs = []
    for token_earning in users_with_tokens:
        user = token_earning.user
        btc_address = getattr(user.userprofile, "btc_address", None)
        tokens_to_send = token_earning.tokens_earned

        if btc_address and tokens_to_send > 0:
            yaml_outputs.append(f"- address: {btc_address}\n  runes:\n    BLT•BACON•TOKENS: {tokens_to_send}")

    # Form the YAML string payload
    yaml_content = "outputs:\n" + "\n".join(yaml_outputs)

    # Payload for POST request
    payload = {"yaml_content": yaml_content}
    ORD_SERVER_URL = settings.ORD_SERVER_URL
    try:
        # Send the request to the ORD server
        response = requests.post(
            f"{ORD_SERVER_URL}/send-bacon-tokens",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
        )
        response_data = response.json()

        # Reset the tokens_earned for all users if the request was successful
        if response.status_code == 200 and response_data.get("success"):
            users_with_tokens.update(tokens_earned=0)
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Tokens successfully sent to all eligible users. If it doesnt appear in the users wallet yet , wait for the miners to confirm the transaction.",
                }
            )
        else:
            return JsonResponse({"status": "error", "message": response_data.get("error", "Unknown error")})

    except requests.RequestException as e:
        return JsonResponse({"status": "error", "message": str(e)})


def pending_transactions_view(request):
    # Fetch all users with non-zero tokens_earned
    pending_transactions = BaconEarning.objects.filter(tokens_earned__gt=0)
    # Prepare a list of user: address: tokens data
    transactions_data = []
    for transaction in pending_transactions:
        user = transaction.user
        btc_address = getattr(user.userprofile, "btc_address", None)
        transactions_data = [{"user": user.username, "address": btc_address, "tokens": transaction.tokens_earned}]

    # If you want to return it as a JSON response:
    return JsonResponse({"pending_transactions": transactions_data})
