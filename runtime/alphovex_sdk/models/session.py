from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..typedefs import Symbol, Timestamp


class SessionType(StrEnum):
    """
    Define the supported trading-session segments.

    Members
    -------
    PRE_MARKET
        Trading session before the regular market opens.
    REGULAR
        Standard regular-hours trading session.
    POST_MARKET
        Trading session immediately following the regular market close.
    EXTENDED
        Trading session outside regular market hours.
    AFTER_HOURS
        Trading session conducted after the regular market closes.
    PRE_OPEN
        Venue preparation or order-entry period before trading opens.
    POST_CLOSE
        Venue period immediately following the market close.
    """

    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    POST_MARKET = "post_market"
    EXTENDED = "extended"
    AFTER_HOURS = "after_hours"
    PRE_OPEN = "pre_open"
    POST_CLOSE = "post_close"


class MarketStatus(StrEnum):
    """
    Define the current trading state of a market or venue.

    Members
    -------
    OPEN
        The market is open and accepting executable orders.
    CLOSED
        The market is closed for trading.
    HALTED
        Trading has been temporarily suspended.
    AUCTION
        The market is conducting an opening, closing, or volatility auction.
    PRE_OPEN
        The venue is in its pre-opening state.
    POST_CLOSE
        The venue is in its post-closing state.
    """

    OPEN = "open"
    CLOSED = "closed"
    HALTED = "halted"
    AUCTION = "auction"
    PRE_OPEN = "pre_open"
    POST_CLOSE = "post_close"


@dataclass(frozen=True, slots=True)
class MarketSession:
    """
    Represent an immutable snapshot of a symbol's trading session.

    The platform creates and updates market-session snapshots. Strategy code
    may inspect the session state but cannot modify an existing instance.

    The session interval includes ``start_time`` and excludes ``end_time``.
    In other words, the interval is represented as
    ``[start_time, end_time)``.

    Attributes
    ----------
    symbol
        Trading symbol associated with the session.
    session_type
        Segment of the trading day represented by the session.
    market_status
        Current trading state of the market or venue.
    start_time
        Timestamp when the session begins.
    end_time
        Timestamp when the session ends.
    timestamp
        Timestamp at which this session snapshot was produced.

    Notes
    -----
    All timestamp values should use the same timezone. The platform should
    normally provide timezone-aware UTC timestamps.
    """

    symbol: Symbol
    session_type: SessionType
    market_status: MarketStatus
    start_time: Timestamp
    end_time: Timestamp
    timestamp: Timestamp

    def contains(self, timestamp: Timestamp) -> bool:
        """
        Determine whether a timestamp falls within the session interval.

        The start timestamp is inclusive and the end timestamp is exclusive.

        Parameters
        ----------
        timestamp
            Timestamp to evaluate.

        Returns
        -------
        bool
            ``True`` when ``timestamp`` is greater than or equal to
            ``start_time`` and less than ``end_time``; otherwise ``False``.

        Examples
        --------
        ```python
        if session.contains(current_time):
            print("Timestamp is inside the session")
        ```
        """
        return self.start_time <= timestamp < self.end_time

    @property
    def is_open(self) -> bool:
        """
        Indicate whether the session is currently open.

        A session is considered open when its market status is ``OPEN`` and
        the snapshot timestamp falls within the session interval.

        Returns
        -------
        bool
            ``True`` when the market is open at ``timestamp``; otherwise
            ``False``.
        """
        return (
            self.market_status == MarketStatus.OPEN
            and self.contains(self.timestamp)
        )

    @property
    def duration_minutes(self) -> float:
        """
        Return the total scheduled duration of the session.

        Returns
        -------
        float
            Number of minutes between ``start_time`` and ``end_time``.
        """
        return (
            self.end_time - self.start_time
        ).total_seconds() / 60.0

    @property
    def remaining_minutes(self) -> float:
        """
        Return the time remaining before the session ends.

        Returns
        -------
        float
            Number of minutes between ``timestamp`` and ``end_time``. Returns
            ``0.0`` when the session has already ended.
        """
        remaining = (
            self.end_time - self.timestamp
        ).total_seconds() / 60.0

        return max(0.0, remaining)