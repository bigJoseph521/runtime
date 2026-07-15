from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Account
from ..typedefs import (
    CashValue, 
    PriceValue, 
    QuantityValue
)

class AccountContext(ABC):

    @abstractmethod
    def get_account_info(self) ->Account:
        ...

    @abstractmethod
    def cash_balance(self) -> CashValue:
        """
        Return Cash Balance
        """
        ...

    @abstractmethod
    def buying_power(self) -> CashValue:
        """
        Return Buying Power
        """
        ...

    @abstractmethod
    def equity(self) -> CashValue:
        """
        Return Equity

        Equity reflects total account value including unrealized PnL.
        """
        ...

    @abstractmethod
    def available_funds(self) -> CashValue:
        """
        Return Available Funds
        """
        ...

    @abstractmethod
    def has_maintenance_margin_deficit(self) -> bool:
        """
        True if equity is below maintenance margin.

        This indicates elevated risk of liquidation.
        This is a simplified check (not exact broker logic).
        """
        ...

    @abstractmethod
    def is_below_initial_margin(self) -> bool:
        """
        True if equity is below initial margin requirement.

        Indicates limited ability to increase exposure.
        """
        ...

    @abstractmethod
    def margin_buffer(self) -> CashValue:
        """
        Remaining buffer above maintenance margin.

        Positive → safe zone  
        Negative → below maintenance (risk zone)
        """
        ...

    @abstractmethod
    def initial_margin_buffer(self) -> CashValue:
        """
        Remaining buffer above initial margin.

        Positive → room to add positions  
        Negative → over-extended
        """
        ...

    @abstractmethod
    def can_cover_notional(self, amount: CashValue) -> bool:
        """
        Check if buying_power can cover a trade notional.

        This is a loose upper-bound check.
        Passing this does NOT guarantee order acceptance.
        """
        ...

    @abstractmethod
    def can_conservatively_cover_notional(self, amount: CashValue) -> bool:
        """
        Check if available_funds can cover a trade notional.

        This is a safer check than using buying_power.
        """
        ...

    @abstractmethod
    def max_theoretical_quantity(self, price: PriceValue) -> QuantityValue:
        """
        Maximum quantity based on buying_power.

        Formula:
            buying_power / price

        This is NOT a safe position size.
        """
        ...

    @abstractmethod
    def max_conservative_quantity(self, price: PriceValue) -> QuantityValue:
        """
        Maximum quantity based on available_funds.

        More conservative than max_theoretical_quantity(),
        but still not a full risk-based size.
        """
        ...
    