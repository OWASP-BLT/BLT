# bacon/bitcoin_utils.py

import logging
from decimal import Decimal, InvalidOperation

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


class BCHPaymentError(Exception):
    # Base exception for BCH payment errors.
    pass


class BCHNetworkError(BCHPaymentError):
    # Network or connectivity error.
    pass


class BCHProviderError(BCHPaymentError):
    # Error returned by the payment provider
    pass


class BCHInvalidResponseError(BCHPaymentError):
    # Invalid or malformed response from provider
    pass


def send_bch_payment(address, amount):
    """
    Send BCH payment using your BCH payment provider.
    Returns transaction ID.
    """

    # 1. Validate amount
    try:
        amount_decimal = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid amount: {amount}")

    if amount_decimal <= 0:
        raise ValueError(f"Amount must be positive: {amount}")

    max_payment = Decimal(str(getattr(settings, "MAX_AUTO_PAYMENT", 100)))
    if amount_decimal > max_payment:
        raise ValueError(f"Amount {amount} exceeds maximum allowed payment {max_payment}")

    # 2. Validate BCH address format (basic checks only)
    if not address or not isinstance(address, str):
        raise ValueError("Missing BCH address")

    if not address.startswith("bitcoincash:"):
        raise ValueError(f"Invalid BCH address: {address}")

    # basic length sanity (CashAddr is long)
    data_part = address.split("bitcoincash:", 1)[1]
    if len(data_part) < 30:
        raise ValueError(f"Invalid BCH address format: {address}")

    # 3. Validate provider configuration
    api_key = getattr(settings, "BCH_API_KEY", None)
    api_url = getattr(settings, "BCH_PAYMENT_API_URL", None)

    if not api_key or not api_url:
        raise ValueError("BCH payment provider credentials not configured")

    # 4. Format amount to 8 decimals
    formatted_amount = f"{amount_decimal:.8f}"

    payload = {
        "to_address": address,
        "amount": formatted_amount,
        "currency": "BCH",
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 5. Send payment request
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        logger.error(f"BCH payment request failed: {str(e)}")
        raise BCHNetworkError("BCH network/payment provider unreachable") from e

    if response.status_code != 200:
        logger.error(f"BCH payment failed ({response.status_code}): {response.text}")
        raise BCHProviderError(f"BCH payment failed: {response.text}")

    data = response.json()

    if "error" in data:
        logger.error(f"BCH payment error: {data['error']}")
        raise BCHProviderError(f"BCH payment failed: {data['error']}")

    tx_id = data.get("transaction_id")
    if not tx_id:
        logger.error("BCH payment response missing transaction_id")
        raise BCHInvalidResponseError("Invalid BCH payment response")

    logger.info(f"BCH payment success: tx {tx_id} to {address}")

    return tx_id
