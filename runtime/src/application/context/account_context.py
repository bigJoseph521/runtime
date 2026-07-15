from __future__ import annotations

from typing import Any

from alphovex_sdk import (
    Account,
    AccountContext,
    CashValue,
    PriceValue,
    QuantityValue
)

class RuntimeAccountContext(AccountContext):
    def __init__(self, account: Account):
        self._account = account
    
    def get_account_info(self) -> Account:
        return Account

    def update(self, new_account: Account):
        self._account = new_account

    @property
    def cash_balance(self) -> CashValue:
        """
        True if account has positive cash.

        Note: Cash ≠ deployable capital in margin accounts.
        """
        return self._account.cash_balance > 0

    @property
    def buying_power(self) -> CashValue:
        """
        True if account has buying power.

        Buying power may include leverage and is NOT a safe sizing limit.
        """
        return self._account.buying_power > 0

    @property
    def equity(self) -> CashValue:
        """
        True if account equity is positive.

        Equity reflects total account value including unrealized PnL.
        """
        return self._account.equity > 0

    @property
    def available_funds(self) -> CashValue:
        """
        True if conservative deployable capital is available.

        This is safer than using buying_power.
        """
        return self._account.available_funds is not None and self._account.available_funds > 0


    @property
    def has_maintenance_margin_deficit(self) -> bool:
        """
        True if equity is below maintenance margin.

        This indicates elevated risk of liquidation.
        This is a simplified check (not exact broker logic).
        """
        if self._account.maintenance_margin is None:
            return False
        return self._account.equity < self._account.maintenance_margin

    @property
    def is_below_initial_margin(self) -> bool:
        """
        True if equity is below initial margin requirement.

        Indicates limited ability to increase exposure.
        """
        return self._account.equity < self._account.initial_margin

    @property
    def margin_buffer(self) -> CashValue:
        """
        Remaining buffer above maintenance margin.

        Positive → safe zone  
        Negative → below maintenance (risk zone)
        """
        return self._account.equity - self._account.maintenance_margin

    @property
    def initial_margin_buffer(self) -> CashValue:
        """
        Remaining buffer above initial margin.

        Positive → room to add positions  
        Negative → over-extended
        """
        return self._account.equity - self._account.initial_margin

    def can_cover_notional(self, amount: CashValue) -> bool:
        """
        Check if buying_power can cover a trade notional.

        This is a loose upper-bound check.
        Passing this does NOT guarantee order acceptance.
        """
        return self._account.buying_power >= amount

    def can_conservatively_cover_notional(self, amount: CashValue) -> bool:
        """
        Check if available_funds can cover a trade notional.

        This is a safer check than using buying_power.
        """
        return self._account.available_funds >= amount

    def max_theoretical_quantity(self, price: PriceValue) -> QuantityValue:
        """
        Maximum quantity based on buying_power.

        Formula:
            buying_power / price

        This is NOT a safe position size.
        """
        if price <= 0:
            return 0.0
        return self._account.buying_power / price

    def max_conservative_quantity(self, price: PriceValue) -> QuantityValue:
        """
        Maximum quantity based on available_funds.

        More conservative than max_theoretical_quantity(),
        but still not a full risk-based size.
        """
        if price <= 0:
            return 0.0
        return self._account.available_funds / price
    
    # TODO
    def update_account(
        self,
        update_info: dict[str, Any]
    ) -> None:
        ...

    
    
