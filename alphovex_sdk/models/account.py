"""
Represent a snapshot of positions and account balance.

Provide a read-only view of current holdings, cash, and exposure at a specific
point in time.

Trading semantics:
    - Quantity is signed: positive (long), negative (short), zero (flat)
    - Prices are per unit (e.g., USD per share)
    - Values and PnL are in account currency (e.g., USD)
    - Exposure uses absolute notional values

Notes:
    - This is a snapshot and does not update in real time
    - Buying power may include leverage and is not a safe sizing limit
    - Available funds are a safer estimate for deployable capital

Examples:
    if position.is_long:
        ...

    if portfolio.balance.can_conservatively_cover_notional(5000):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
from ..typedefs import CashValue

@dataclass
class Account:
    """
    Represents a normalized snapshot of cash, equity, and margin.

    Broker field names and exact semantics differ; treat ``available_funds`` as
    the conservative deployable capital figure and ``buying_power`` only as an
    upper bound that may include leverage.

    Attributes
    ----------
    cash_balance:
        Reported cash in the account.
    buying_power:
        Maximum theoretical trading capacity (may include margin).
    equity:
        Total account value including positions and unrealized PnL.
    initial_margin:
        Margin required to support current exposure.
    maintenance_margin:
        Minimum margin to maintain open positions.
    available_funds:
        Conservative estimate of capital available for new risk.
    """
    broker: str
    cash_balance: CashValue
    buying_power: CashValue
    equity: CashValue
    initial_margin: CashValue
    maintenance_margin: CashValue
    available_funds: CashValue

    total_unrealized_pnl: CashValue | None  = None
    total_realized_pnl: CashValue | None  = None
