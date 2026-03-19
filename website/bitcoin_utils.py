# bacon/bitcoin_utils.py

import logging

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

def get_sighash_type(txid):
    """
    Retrieves the SIGHASH type from the first input of a confirmed transaction.
    """
    rpc_client = get_rpc_client()
    
    SIGHASH_MAP = {
        0x01: "SIGHASH_ALL",
        0x02: "SIGHASH_NONE",
        0x03: "SIGHASH_SINGLE",
        0x80: "SIGHASH_ANYONECANPAY",
        0x81: "SIGHASH_ALL_ANYONECANPAY",
    }
    
    try:
        tx = rpc_client.getrawtransaction(txid, True)

        first_vin = tx.get('vin', [{}])[0]

        witness = first_vin.get('txinwitness', [])
        if witness:
            signature_hex = witness[0]
        else:
            script_sig = first_vin.get('scriptSig',{}).get('hex','')
            signature_hex = script_sig
        if not signature_hex:
            return "UNKNOWN"
        sighash_byte = int(signature_hex[-2:], 16)
        
        return SIGHASH_MAP.get(sighash_byte, f"CUSTOM_{sighash_byte}")

    except Exception as e:
        logger.error(f"Failed to extract SIGHASH for {txid}: {e}")
        return "ERROR"
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
