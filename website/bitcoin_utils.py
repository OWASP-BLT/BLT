# bacon/bitcoin_utils.py

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from django.conf import settings

from website.models import BaconToken


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
        print(f"Error creating token: {e}")
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

