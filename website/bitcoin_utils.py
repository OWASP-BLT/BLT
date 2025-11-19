# bacon/bitcoin_utils.py

import logging
from decimal import Decimal

import requests
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from django.conf import settings

from website.models import BaconToken

logger = logging.getLogger(__name__)


def get_rpc_client():
    return AuthServiceProxy(
        f"http://{settings.BITCOIN_RPC_USER}:{settings.BITCOIN_RPC_PASSWORD}@{settings.BITCOIN_RPC_HOST}:{settings.BITCOIN_RPC_PORT}"
    )


def create_bacon_token(user, contribution):
    rpc_client = get_rpc_client()

    try:
        asset_name = "BACON"
        amount = 10
        user_identifier = f"user-{user.id}"

        txid = rpc_client.issue_asset(asset_name, amount, user_identifier)

        contribution.txid = txid
        contribution.save()

        token = BaconToken.objects.create(user=user, amount=amount, contribution=contribution, token_id=txid)
        return token

    except JSONRPCException as e:
        logger.error(f"Error creating token: {e}")
        return None


def issue_asset(asset_name, amount, identifier):
    """
    This function is custom script or RPC call that creates a new asset on Bitcoin using Runes.
    """
    rpc_client = get_rpc_client()

    address = rpc_client.getnewaddress()
    txid = rpc_client.sendtoaddress(
        address,
        0.01,
        "",
        "",
        True,
        False,
        1,
        "none",
        {"issue_asset": {"name": asset_name, "amount": amount, "identifier": identifier}},
    )

    # The transaction ID (txid) can be used to track the issuance on the blockchain.
    return txid


def send_bch_payment(address, amount):
    """
    Send BCH payment using your BCH payment provider.
    Returns transaction ID.
    """

    # Validate BCH address format
    if not address.startswith("bitcoincash:"):
        raise ValueError(f"Invalid BCH address: {address}")

    # Format amount to 8 decimals (required for BCH)
    formatted_amount = f"{Decimal(amount):.8f}"

    url = settings.BCH_PAYMENT_API_URL

    payload = {"to_address": address, "amount": formatted_amount, "currency": "BCH"}

    headers = {"Authorization": f"Bearer {settings.BCH_API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        logger.error(f"BCH payment request failed: {str(e)}")
        raise Exception("BCH network/payment provider unreachable")

    # Handle non-200 result
    if response.status_code != 200:
        logger.error(f"BCH payment failed ({response.status_code}): {response.text}")
        raise Exception(f"BCH payment failed: {response.text}")

    data = response.json()

    # Check if provider sent an error
    if "error" in data:
        logger.error(f"BCH payment error: {data['error']}")
        raise Exception(f"BCH payment failed: {data['error']}")

    # Ensure transaction_id exists
    tx_id = data.get("transaction_id")
    if not tx_id:
        logger.error("BCH payment response missing transaction_id")
        raise Exception("Invalid BCH payment response")

    logger.info(f"BCH payment success: tx {tx_id} to {address}")

    return tx_id
