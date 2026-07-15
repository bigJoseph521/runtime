from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .order import OrderId
from ..typedefs import (
    InstrumentId, 
    Timestamp, 
    QuantityValue, 
    PriceValue
)


@dataclass(frozen=True, slots=True)
class Fill:
    """
    Represents an execution fill for an order.

    A fill is created when some or all of an order quantity is executed.
    Strategies receive fill events through lifecycle callbacks such as
    ``on_fill()``.

    Notes
    -----
    - A single order may produce multiple fills.
    - A fill does not guarantee that the full order quantity is complete.
    - Use the related ``Order`` object to inspect the latest overall order state.

    Attributes
    ----------
    order_id:
        Identifier of the order that produced this fill.
    instrument_id:
        Identifier of the instrument that was filled.
    qty:
        Quantity filled in this execution event.
    price:
        Execution price for this fill.
    occurred_at:
        Timestamp when the fill occurred.
    """

    order_id: OrderId
    instrument_id: InstrumentId
    qty: QuantityValue
    price: PriceValue
    occurred_at: Timestamp