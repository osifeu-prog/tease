
import logging
from decimal import Decimal
from typing import Optional, Dict

from web3 import Web3

from app.core.config import settings

logger = logging.getLogger(__name__)

_w3: Optional[Web3] = None
_token_contract = None


def _get_w3() -> Optional[Web3]:
    """Return a cached Web3 instance or None if RPC is not configured/available."""
    global _w3
    if _w3 is not None:
        return _w3

    rpc_url = settings.BSC_RPC_URL
    if not rpc_url:
        logger.warning("BSC_RPC_URL is not configured")
        return None

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            logger.warning("Failed to connect to BSC RPC at %s", rpc_url)
            return None
        _w3 = w3
        return _w3
    except Exception as e:
        logger.exception("Error creating Web3 provider: %s", e)
        return None


def _get_token_contract():
    """Return a minimal ERC‑20 contract instance for the SLH token, if possible."""
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
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function",
            },
        ]
        _token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.SLH_TOKEN_ADDRESS),
            abi=abi,
        )
    except Exception as e:
        logger.exception("Error creating SLH token contract: %s", e)
        _token_contract = None

    return _token_contract


def get_onchain_balances(address: str) -> Optional[Dict[str, Decimal]]:
    """Return on-chain BNB & SLH balances for a given BSC address.

    Returns a dict: {"bnb": Decimal | None, "slh": Decimal | None} or None if
    Web3 is not available.
    """
    w3 = _get_w3()
    if w3 is None:
        return None

    if not address:
        return None

    try:
        checksum = Web3.to_checksum_address(address)
    except Exception as e:
        logger.warning("Invalid address for on-chain balance: %s (err=%s)", address, e)
        return None

    bnb: Optional[Decimal] = None
    slh: Optional[Decimal] = None

    # BNB balance
    try:
        wei = w3.eth.get_balance(checksum)
        bnb = Decimal(wei) / Decimal(10 ** 18)
    except Exception as e:
        logger.warning("Failed to fetch BNB balance: %s", e)

    # SLH token balance
    if settings.SLH_TOKEN_ADDRESS:
        try:
            contract = _get_token_contract()
            if contract is not None:
                raw = contract.functions.balanceOf(checksum).call()
                decimals = int(settings.SLH_TOKEN_DECIMALS or 18)
                slh = Decimal(raw) / Decimal(10 ** decimals)
        except Exception as e:
            logger.warning("Failed to fetch SLH token balance: %s", e)

    return {"bnb": bnb, "slh": slh}


# ===== Sending helpers for admin tools =====

def _get_private_key_bytes() -> str:
    pk = settings.COMMUNITY_WALLET_PRIVATE_KEY
    if not pk:
        raise RuntimeError("COMMUNITY_WALLET_PRIVATE_KEY is not configured")

    pk = pk.strip()
    if not pk.startswith("0x"):
        raise RuntimeError("COMMUNITY_WALLET_PRIVATE_KEY must start with 0x")
    # Web3 accepts both hex string or bytes; we keep hex string here
    return pk


def _get_community_address(w3: Web3) -> str:
    """Derive community wallet address from the configured private key."""
    pk = _get_private_key_bytes()
    acct = w3.eth.account.from_key(pk)
    return acct.address


def send_bnb_from_community(to_address: str, amount_bnb: Decimal) -> str:
    """Send native BNB from the community wallet.

    Returns transaction hash as hex string.
    """
    w3 = _get_w3()
    if w3 is None:
        raise RuntimeError("Web3 is not available (check BSC_RPC_URL)")

    if amount_bnb <= 0:
        raise ValueError("Amount must be positive")

    try:
        to_checksum = Web3.to_checksum_address(to_address)
    except Exception as e:
        raise ValueError(f"Invalid destination address: {to_address}") from e

    pk = _get_private_key_bytes()
    from_addr = _get_community_address(w3)

    # Build transaction
    value_wei = int(amount_bnb * Decimal(10 ** 18))
    try:
        gas_price = w3.eth.gas_price
    except Exception:
        gas_price = w3.to_wei(1, "gwei")

    txn = {
        "from": from_addr,
        "to": to_checksum,
        "value": value_wei,
        "gasPrice": gas_price,
        "nonce": w3.eth.get_transaction_count(from_addr),
    }

    # Estimate gas (best effort)
    try:
        gas_limit = w3.eth.estimate_gas(txn)
    except Exception:
        gas_limit = 21000
    txn["gas"] = gas_limit

    signed = w3.eth.account.sign_transaction(txn, private_key=pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()


def send_slh_from_community(to_address: str, amount_slh: Decimal) -> str:
    """Send SLH tokens (ERC20) from the community wallet.

    Returns transaction hash as hex string.
    """
    w3 = _get_w3()
    if w3 is None:
        raise RuntimeError("Web3 is not available (check BSC_RPC_URL)")

    if amount_slh <= 0:
        raise ValueError("Amount must be positive")

    try:
        to_checksum = Web3.to_checksum_address(to_address)
    except Exception as e:
        raise ValueError(f"Invalid destination address: {to_address}") from e

    contract = _get_token_contract()
    if contract is None:
        raise RuntimeError("Token contract is not available (check SLH_TOKEN_ADDRESS)")

    pk = _get_private_key_bytes()
    from_addr = _get_community_address(w3)

    decimals = int(settings.SLH_TOKEN_DECIMALS or 18)
    raw_amount = int(amount_slh * Decimal(10 ** decimals))

    txn = contract.functions.transfer(to_checksum, raw_amount).build_transaction(
        {
            "from": from_addr,
            "nonce": w3.eth.get_transaction_count(from_addr),
            "gasPrice": w3.eth.gas_price,
        }
    )

    # Estimate gas (best effort)
    try:
        gas_limit = w3.eth.estimate_gas(txn)
    except Exception:
        gas_limit = 200000
    txn["gas"] = gas_limit

    signed = w3.eth.account.sign_transaction(txn, private_key=pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return tx_hash.hex()
