import logging
from decimal import Decimal
from typing import Optional, Dict

from web3 import Web3

from app.core.config import settings

logger = logging.getLogger(__name__)

_w3: Optional[Web3] = None
_token_contract = None


def _get_w3() -> Optional[Web3]:
    global _w3
    if _w3 is not None:
        return _w3

    if not settings.BSC_RPC_URL:
        logger.warning("BSC_RPC_URL is not configured – on-chain balances disabled")
        return None

    try:
        _w3 = Web3(Web3.HTTPProvider(settings.BSC_RPC_URL))
        if not _w3.is_connected():
            logger.warning("Web3 could not connect to BSC RPC at %s", settings.BSC_RPC_URL)
            _w3 = None
    except Exception as e:
        logger.exception("Error creating Web3 client: %s", e)
        _w3 = None

    return _w3


def _get_token_contract():
    global _token_contract
    if _token_contract is not None:
        return _token_contract

    w3 = _get_w3()
    if w3 is None or not settings.SLH_TOKEN_ADDRESS:
        return None

    try:
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function",
            }
        ]
        _token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.SLH_TOKEN_ADDRESS),
            abi=abi,
        )
    except Exception as e:
        logger.exception("Error creating token contract: %s", e)
        _token_contract = None

    return _token_contract


def get_onchain_balances(address: str) -> Optional[Dict[str, Decimal]]:
    """מחזיר מילון עם BNB ו-SLH לפי כתובת, או None אם אי אפשר לחשב."""
    if not address:
        return None

    w3 = _get_w3()
    if w3 is None:
        return None

    try:
        checksum = Web3.to_checksum_address(address)
    except Exception:
        logger.warning("Invalid BNB address for on-chain balance: %s", address)
        return None

    bnb: Optional[Decimal] = None
    slh: Optional[Decimal] = None

    # BNB balance
    try:
        wei = w3.eth.get_balance(checksum)
        bnb = Decimal(wei) / Decimal(10**18)
    except Exception as e:
        logger.warning("Failed to fetch BNB balance: %s", e)

    # SLH token balance
    if settings.SLH_TOKEN_ADDRESS:
        try:
            contract = _get_token_contract()
            if contract is not None:
                raw = contract.functions.balanceOf(checksum).call()
                decimals = int(settings.SLH_TOKEN_DECIMALS or 18)
                slh = Decimal(raw) / Decimal(10**decimals)
        except Exception as e:
            logger.warning("Failed to fetch SLH token balance: %s", e)

    return {"bnb": bnb, "slh": slh}

def send_bnb_from_community(to_address: str, amount_bnb: Decimal) -> str:
    """Send BNB from the community hot wallet to a target address.

    Returns the transaction hash (hex). Raises ValueError / RuntimeError on errors.
    """
    w3 = _get_w3()
    if w3 is None:
        raise RuntimeError("Web3 provider not available (BSC_RPC_URL is missing or invalid).")

    if not settings.COMMUNITY_WALLET_ADDRESS or not settings.COMMUNITY_WALLET_PRIVATE_KEY:
        raise RuntimeError("Community wallet sending is not configured (address/private key missing).")

    try:
        from_addr = w3.to_checksum_address(settings.COMMUNITY_WALLET_ADDRESS)
        to_addr = w3.to_checksum_address(to_address)
    except Exception as e:  # noqa: BLE001
        raise ValueError("Invalid BNB address.") from e

    # Build a simple BNB transfer tx
    nonce = w3.eth.get_transaction_count(from_addr)
    value_wei = int(Decimal(amount_bnb) * Decimal(10**18))
    tx = {
        "from": from_addr,
        "to": to_addr,
        "value": value_wei,
        "nonce": nonce,
        "gas": 21000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    }

    signed = w3.eth.account.sign_transaction(
        tx,
        private_key=settings.COMMUNITY_WALLET_PRIVATE_KEY,
    )
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()


def send_slh_from_community(to_address: str, amount_slh: Decimal) -> str:
    """Send SLH tokens from the community hot wallet to a target address.

    Uses the SLH_TOKEN_ADDRESS + SLH_TOKEN_DECIMALS configuration.
    Returns the transaction hash (hex).
    """
    w3 = _get_w3()
    if w3 is None:
        raise RuntimeError("Web3 provider not available (BSC_RPC_URL is missing or invalid).")

    if not settings.COMMUNITY_WALLET_ADDRESS or not settings.COMMUNITY_WALLET_PRIVATE_KEY:
        raise RuntimeError("Community wallet sending is not configured (address/private key missing).")

    contract = _get_token_contract()
    if contract is None:
        raise RuntimeError("Token contract is not configured correctly (SLH_TOKEN_ADDRESS missing?).")

    try:
        from_addr = w3.to_checksum_address(settings.COMMUNITY_WALLET_ADDRESS)
        to_addr = w3.to_checksum_address(to_address)
    except Exception as e:  # noqa: BLE001
        raise ValueError("Invalid BSC address.") from e

    decimals = settings.SLH_TOKEN_DECIMALS or 18
    amount_raw = int(Decimal(amount_slh) * Decimal(10**decimals))

    nonce = w3.eth.get_transaction_count(from_addr)

    tx = contract.functions.transfer(to_addr, amount_raw).build_transaction(
        {
            "from": from_addr,
            "nonce": nonce,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
        }
    )

    # Estimate gas conservatively
    try:
        gas_estimate = w3.eth.estimate_gas(tx)
    except Exception:  # noqa: BLE001
        gas_estimate = 200_000

    tx["gas"] = gas_estimate

    signed = w3.eth.account.sign_transaction(
        tx,
        private_key=settings.COMMUNITY_WALLET_PRIVATE_KEY,
    )
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()

