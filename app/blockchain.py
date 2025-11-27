import logging
from decimal import Decimal

from web3 import Web3
from web3.exceptions import Web3Exception

from app.core.config import settings

logger = logging.getLogger(__name__)

# === Web3 Setup ===

_w3: Web3 | None = None


def _get_w3() -> Web3 | None:
    """
    יוצר/מחזיר אובייקט Web3 לפי BSC_RPC_URL מה־env.
    אם אין או לא תקין – נחזיר None כדי לא להפיל את הבוט.
    """
    global _w3
    if _w3 is not None:
        return _w3

    rpc_url = getattr(settings, "BSC_RPC_URL", None)
    if not rpc_url:
        logger.warning("BSC_RPC_URL is not configured – on-chain balances disabled")
        return None

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            logger.warning("Web3 could not connect to BSC RPC: %s", rpc_url)
            return None
        _w3 = w3
        logger.info("Web3 connected to BSC RPC")
        return _w3
    except Exception as e:
        logger.warning("Failed to initialize Web3: %s", e)
        return None


# === ERC-20 SLH Token ===

# ABI מינימלי ל־ERC-20: balanceOf, decimals
_ERC20_MIN_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]


def _get_slh_token_contract(w3: Web3):
    token_address = getattr(settings, "SLH_TOKEN_ADDRESS", None)
    if not token_address:
        logger.warning("SLH_TOKEN_ADDRESS not configured – on-chain SLH disabled")
        return None

    try:
        checksum = w3.to_checksum_address(token_address)
    except ValueError:
        logger.warning("Invalid SLH_TOKEN_ADDRESS: %s", token_address)
        return None

    return w3.eth.contract(address=checksum, abi=_ERC20_MIN_ABI)


def _get_slh_decimals(w3: Web3, contract) -> int:
    """
    מנסה להביא decimals מהחוזה. אם נכשל, נשתמש ב־SLH_TOKEN_DECIMALS מה־env,
    ואם גם זה לא – ניפול לברירת מחדל 15 (כמו במטאמסק אצלך).
    """
    # שלב 1 – env
    try:
        env_dec = int(getattr(settings, "SLH_TOKEN_DECIMALS", 15))
    except Exception:
        env_dec = 15

    if contract is None:
        return env_dec

    # שלב 2 – ניסיון מהחוזה
    try:
        onchain_dec = contract.functions.decimals().call()
        return int(onchain_dec)
    except Web3Exception as e:
        logger.warning("Could not fetch SLH decimals from chain: %s", e)
    except Exception as e:
        logger.warning("Error reading decimals from contract: %s", e)

    return env_dec


# === Public API ===

def get_onchain_balances(bnb_address: str) -> dict[str, Decimal | None]:
    """
    מחזיר מילון עם:
      {
        "bnb": Decimal | None,
        "slh": Decimal | None
      }

    אם אין RPC או טעות – מחזירים None בשדות הרלוונטיים.
    """
    w3 = _get_w3()
    if w3 is None:
        # אין חיבור ל-RPC
        return {"bnb": None, "slh": None}

    # Normalise address
    try:
        checksum = w3.to_checksum_address(bnb_address)
    except ValueError:
        logger.warning("Invalid BNB address given to get_onchain_balances: %s", bnb_address)
        return {"bnb": None, "slh": None}

    bnb: Decimal | None = None
    slh: Decimal | None = None

    # --- BNB native balance ---
    try:
        balance_wei = w3.eth.get_balance(checksum)
        bnb = Decimal(balance_wei) / Decimal(10**18)
    except Web3Exception as e:
        logger.warning("Failed to fetch BNB balance: %s", e)
    except Exception as e:
        logger.warning("Unexpected error fetching BNB balance: %s", e)

    # --- SLH token balance ---
    try:
        token_contract = _get_slh_token_contract(w3)
        if token_contract is not None:
            decimals = _get_slh_decimals(w3, token_contract)
            raw = token_contract.functions.balanceOf(checksum).call()
            slh = Decimal(raw) / Decimal(10**decimals)
        else:
            slh = None
    except Web3Exception as e:
        logger.warning("Failed to fetch SLH token balance: %s", e)
        slh = None
    except Exception as e:
        logger.warning("Unexpected error fetching SLH token balance: %s", e)
        slh = None

    return {"bnb": bnb, "slh": slh}
