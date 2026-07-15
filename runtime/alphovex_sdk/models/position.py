from __future__ import annotations

from dataclasses import dataclass

from ..typedefs import (
    CashValue,
    InstrumentId,
    PriceValue,
    QuantityValue,
    Symbol,
    Timestamp,
)
from .order import OrderSide


@dataclass(frozen=True, slots=True)
class Position:
    """
    Represent an immutable snapshot of an open position.

    Position direction is determined by the signed quantity. A positive
    quantity represents a long position, a negative quantity represents a
    short position, and zero represents a flat position.

    The platform creates and updates position snapshots from portfolio and
    broker events. Strategy code should read position data but must not modify
    it.

    Attributes
    ----------
    symbol
        Trading symbol of the instrument.
    quantity
        Signed position quantity. Positive values indicate a long position,
        negative values indicate a short position, and zero indicates no open
        position.
    average_price
        Volume-weighted average entry price of the open quantity.
    market_price
        Current mark price used to value the position.
    market_value
        Current value of the position in the account currency.
    unrealized_pnl
        Unrealized profit or loss in the account currency.
    timestamp
        Timestamp when the position snapshot was produced.
    instrument_id
        Platform or broker instrument identifier, or ``None`` when not
        available.
    last_price
        Most recently reported market price, or ``None`` when not available.
    cost_basis
        Total cost basis of the open position, or ``None`` when not available.
    unrealized_pnl_pct
        Unrealized profit or loss as a decimal ratio, or ``None`` when it
        cannot be calculated.
    realized_pnl
        Realized profit or loss associated with the position, or ``None`` when
        not available.
    side
        Platform-reported position side, or ``None`` when direction should be
        inferred from ``quantity``.

    Notes
    -----
    Instances are immutable. Platform updates produce a new ``Position``
    snapshot rather than modifying an existing instance.

    Fields prefixed with an underscore contain optional platform-managed
    metadata. Strategy code should prefer public properties or fields when
    equivalent information is available.
    """

    symbol: Symbol
    quantity: QuantityValue
    average_price: PriceValue
    market_price: PriceValue
    market_value: CashValue
    unrealized_pnl: CashValue
    timestamp: Timestamp

    instrument_id: InstrumentId | None = None
    last_price: PriceValue | None = None
    cost_basis: CashValue | None = None
    unrealized_pnl_pct: float | None = None
    realized_pnl: CashValue | None = None
    side: OrderSide | None = None