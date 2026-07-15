from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ..errors import InvalidValueError


@dataclass(slots=True, frozen=True)
class Bar:
    """
    Represent an immutable OHLCV market-data bar.

    The timestamp represents the opening time of the bar. Derived price and
    candlestick values are calculated from the stored OHLC prices.

    Attributes
    ----------
    open
        First traded price during the bar period.
    high
        Highest traded price during the bar period.
    low
        Lowest traded price during the bar period.
    close
        Last traded price during the bar period.
    volume
        Total traded volume during the bar period.
    ts
        Opening timestamp of the bar.
    """

    open: float
    high: float
    low: float
    close: float
    volume: float
    ts: datetime

    def get_price(self, price_type: str) -> float:
        """
        Return the requested price value.

        Parameters
        ----------
        price_type
            Price representation to return. Supported values are ``"open"``,
            ``"high"``, ``"low"``, ``"close"``, ``"typical"``, and
            ``"weighted"``. Matching is case-insensitive.

        Returns
        -------
        float
            Requested price value.

        Raises
        ------
        InvalidValueError
            Raised when ``price_type`` is unsupported.

        Examples
        --------
        ```python
        close_price = bar.get_price("close")
        typical_price = bar.get_price("typical")
        ```
        """
        normalized_price_type = price_type.lower()

        if normalized_price_type == "open":
            return self.open
        if normalized_price_type == "close":
            return self.close
        if normalized_price_type == "high":
            return self.high
        if normalized_price_type == "low":
            return self.low
        if normalized_price_type == "typical":
            return self.typical_price
        if normalized_price_type == "weighted":
            return self.weighted_price
        if normalized_price_type == "median":
            return self.median_price

        raise InvalidValueError(message="Unsupported price type")

    @property
    def is_bullish(self) -> bool:
        """
        Indicate whether the bar closed above its opening price.

        Returns
        -------
        bool
            ``True`` when the closing price is greater than the opening price;
            otherwise ``False``.
        """
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """
        Indicate whether the bar closed below its opening price.

        Returns
        -------
        bool
            ``True`` when the closing price is less than the opening price;
            otherwise ``False``.
        """
        return self.close < self.open

    @property
    def body(self) -> float:
        """
        Return the absolute size of the candlestick body.

        Returns
        -------
        float
            Absolute difference between the opening and closing prices.
        """
        return abs(self.open - self.close)

    @property
    def price_range(self) -> float:
        """
        Return the full price range of the bar.

        Returns
        -------
        float
            Difference between the highest and lowest prices.
        """
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        """
        Return the size of the upper candlestick wick.

        Returns
        -------
        float
            Difference between the highest price and the greater of the
            opening and closing prices.
        """
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        """
        Return the size of the lower candlestick wick.

        Returns
        -------
        float
            Difference between the lesser of the opening and closing prices
            and the lowest price.
        """
        return min(self.open, self.close) - self.low

    @property
    def median_price(self) -> float:
        """
        Return the midpoint of the bar's highest and lowest prices.

        Returns
        -------
        float
            Average of the highest and lowest prices.
        """
        return (self.high + self.low) / 2

    @property
    def typical_price(self) -> float:
        """
        Return the typical price of the bar.

        The typical price is calculated as:

        ``(high + low + close) / 3``

        Returns
        -------
        float
            Typical price of the bar.
        """
        return (self.high + self.low + self.close) / 3

    @property
    def weighted_price(self) -> float:
        """
        Return the weighted closing price of the bar.

        The weighted price is calculated as:

        ``(high + low + 2 * close) / 4``

        Returns
        -------
        float
            Weighted closing price of the bar.
        """
        return (self.high + self.low + 2 * self.close) / 4


@dataclass(slots=True, frozen=True)
class Tick:
    """
    Represent an immutable executed-trade tick.

    Attributes
    ----------
    ts
        Timestamp when the trade was executed.
    price
        Execution price of the trade.
    volume
        Executed trade volume.
    """

    ts: datetime
    price: float
    volume: float


@dataclass(slots=True, frozen=True)
class Quote:
    """
    Represent an immutable bid-and-ask market quote.

    Attributes
    ----------
    ts
        Timestamp of the quote.
    bid_price
        Highest price currently offered by buyers.
    bid_size
        Quantity available at the bid price.
    ask_price
        Lowest price currently offered by sellers.
    ask_size
        Quantity available at the ask price.
    """

    ts: datetime
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float

    @property
    def mid(self) -> float:
        """
        Return the midpoint between the bid and ask prices.

        Returns
        -------
        float
            Average of the bid and ask prices.
        """
        return (self.bid_price + self.ask_price) / 2

    @property
    def spread(self) -> float:
        """
        Return the bid-ask spread.

        Returns
        -------
        float
            Difference between the ask price and bid price.
        """
        return self.ask_price - self.bid_price


class FinancialFactor(StrEnum):
    """
    Define financial factors available for symbol selection.

    Financial factors can be used to rank securities, filter a symbol
    universe, and construct factor-based trading models.

    Members
    -------
    PE_RATIO
        Price-to-earnings valuation ratio.
    PB_RATIO
        Price-to-book valuation ratio.
    EV_EBITDA
        Enterprise-value-to-EBITDA valuation ratio.
    PRICE_TO_SALES
        Price-to-sales valuation ratio.
    PRICE_TO_FREE_CASH_FLOW
        Price-to-free-cash-flow valuation ratio.
    ROE
        Return on equity.
    ROA
        Return on assets.
    EPS
        Earnings per share.
    FREE_CASH_FLOW
        Free cash flow.
    NET_INCOME
        Net income after expenses and taxes.
    OPERATING_INCOME
        Income generated from core business operations.
    REVENUE
        Total revenue from goods and services.
    EBITDA
        Earnings before interest, taxes, depreciation, and amortization.
    GROSS_PROFIT
        Revenue remaining after cost of revenue.
    DEBT_TO_EQUITY
        Ratio of total debt to shareholder equity.
    CURRENT_RATIO
        Ratio of current assets to current liabilities.
    QUICK_RATIO
        Liquidity ratio excluding inventory.
    CASH_RATIO
        Ratio of cash and equivalents to current liabilities.
    CASH_POSITION
        Cash and cash-equivalent balance.
    TOTAL_DEBT
        Total current and long-term debt.
    MARKET_CAP
        Total market value of outstanding shares.
    DIVIDEND_YIELD
        Annual dividend return relative to stock price.
    SHARES_OUTSTANDING
        Total number of outstanding shares.
    """

    # Value factors
    PE_RATIO = "price_to_earnings"
    PB_RATIO = "price_to_book"
    EV_EBITDA = "ev_to_ebitda"
    PRICE_TO_SALES = "price_to_sales"
    PRICE_TO_FREE_CASH_FLOW = "price_to_free_cash_flow"

    # Quality factors
    ROE = "return_on_equity"
    ROA = "return_on_assets"
    EPS = "earnings_per_share"
    FREE_CASH_FLOW = "free_cash_flow"

    # Earnings factors
    NET_INCOME = "net_income"
    OPERATING_INCOME = "operating_income"
    REVENUE = "revenue"
    EBITDA = "ebitda"
    GROSS_PROFIT = "gross_profit"

    # Risk and liquidity factors
    DEBT_TO_EQUITY = "debt_to_equity"
    CURRENT_RATIO = "current"
    QUICK_RATIO = "quick"
    CASH_RATIO = "cash"
    CASH_POSITION = "cash_and_equivalents"
    TOTAL_DEBT = "total_debt"

    # Market factors
    MARKET_CAP = "market_cap"
    DIVIDEND_YIELD = "dividend_yield"
    SHARES_OUTSTANDING = "shares_outstanding"