from decimal import Decimal


def get_onchain_balances(address: str) -> dict:
    """
    Placeholder for real BSC integration.
    Currently returns 0/0 so the bot works without external RPC.
    """
    return {
        "bnb": Decimal("0"),
        "slh": Decimal("0"),
    }
