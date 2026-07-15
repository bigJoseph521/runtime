from __future__ import annotations

from collections import deque
from math import sqrt
from typing import Final

import numpy as np

from ..errors import InvalidValueError
from ..typedefs import PriceValue
from ..models import Bar


Number = int | float

VALID_PRICE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "open",
        "close",
        "high",
        "low",
        "typical",
        "weighted",
        "median"
    }
)


def validate_price_type(price_type: str) -> None:
    """
    Validate a supported bar price type.

    Parameters
    ----------
    price_type
        Price type to validate. Supported values are ``"open"``, ``"close"``,
        ``"high"``, ``"low"``, ``"typical"``,``"weighted"``, and ``"median"``.

    Raises
    ------
    InvalidValueError
        Raised when ``price_type`` is not supported.
    """
    if price_type not in VALID_PRICE_TYPES:
        raise InvalidValueError(
            message=f"Invalid price type: {price_type}",
            details={
                "price_type": price_type,
                "valid_price_types": sorted(VALID_PRICE_TYPES),
            },
        )

def to_price_value(value: object) -> PriceValue:
    """
    Convert a raw value to a price value.

    Existing floating-point values are returned directly. Other values are
    converted to strings before conversion to avoid unsupported direct
    conversions from custom numeric objects.

    Parameters
    ----------
    value
        Raw value to convert.

    Returns
    -------
    PriceValue
        Floating-point price value.

    Raises
    ------
    TypeError
        Raised when ``value`` cannot be converted to a string or float.
    ValueError
        Raised when the string representation of ``value`` is not numeric.
    """
    if isinstance(value, float):
        return value

    return float(str(value))


def _to_float(value: Number) -> float:
    """
    Convert a supported numeric value to ``float``.

    Parameters
    ----------
    value
        Integer or floating-point value to convert.

    Returns
    -------
    float
        Converted floating-point value.
    """
    return float(value)


class RollingSum:
    """
    Maintain a fixed-size rolling sum and mean.

    Values are stored from oldest to newest. Committed values are added with
    ``push()``. Preview methods calculate temporary values using a forming
    observation without modifying committed state.

    Parameters
    ----------
    size
        Number of committed observations in the rolling window.

    Raises
    ------
    ValueError
        Raised when ``size`` is not greater than zero.

    Notes
    -----
    This helper is suitable for simple moving averages, rolling volume sums,
    and similar fixed-window calculations.
    """

    __slots__ = ("size", "_values", "_total")

    def __init__(self, size: int) -> None:
        """
        Initialize a rolling-sum window.

        Parameters
        ----------
        size
            Number of observations in the rolling window.

        Raises
        ------
        ValueError
            Raised when ``size`` is not greater than zero.
        """
        if size <= 0:
            raise ValueError("size must be greater than 0")

        self.size = size
        self._values: deque[float] = deque()
        self._total = 0.0

    def reset(self) -> None:
        """
        Clear all committed values and reset the accumulated sum.
        """
        self._values.clear()
        self._total = 0.0

    @property
    def ready(self) -> bool:
        """
        Indicate whether the rolling window is full.

        Returns
        -------
        bool
            ``True`` when the number of committed values equals ``size``;
            otherwise ``False``.
        """
        return len(self._values) == self.size

    @property
    def count(self) -> int:
        """
        Return the number of committed values.

        Returns
        -------
        int
            Current number of values in the rolling window.
        """
        return len(self._values)

    @property
    def values(self) -> tuple[float, ...]:
        """
        Return committed values ordered from oldest to newest.

        Returns
        -------
        tuple[float, ...]
            Immutable snapshot of the rolling window.
        """
        return tuple(self._values)

    def push(self, value: Number) -> float | None:
        """
        Commit a value to the rolling window.

        When the window is already full, the oldest value is removed before
        the new value is appended.

        Parameters
        ----------
        value
            Numeric value to commit.

        Returns
        -------
        float | None
            Rolling sum when the window is full, or ``None`` while the window
            is still warming up.
        """
        value = _to_float(value)

        if len(self._values) == self.size:
            oldest = self._values.popleft()
            self._total -= oldest

        self._values.append(value)
        self._total += value

        return self.sum()

    def sum(self) -> float | None:
        """
        Return the committed rolling sum.

        Returns
        -------
        float | None
            Sum of committed values when the window is full, or ``None``
            while the window is still warming up.
        """
        if not self.ready:
            return None

        return self._total

    def mean(self) -> float | None:
        """
        Return the committed rolling mean.

        Returns
        -------
        float | None
            Mean of committed values when the window is full, or ``None``
            while the window is still warming up.
        """
        if not self.ready:
            return None

        return self._total / self.size

    def preview_sum(self, current_value: Number) -> float | None:
        """
        Preview the rolling sum using a temporary current value.

        The preview combines the latest ``size - 1`` committed values with
        ``current_value``. Committed state is not modified.

        Parameters
        ----------
        current_value
            Forming or temporary value to include in the preview.

        Returns
        -------
        float | None
            Previewed rolling sum, or ``None`` when insufficient committed
            values are available.
        """
        current_value = _to_float(current_value)

        if self.size == 1:
            return current_value

        if len(self._values) < self.size - 1:
            return None

        if len(self._values) == self.size:
            return self._total - self._values[0] + current_value

        return self._total + current_value

    def preview_mean(self, current_value: Number) -> float | None:
        """
        Preview the rolling mean using a temporary current value.

        Parameters
        ----------
        current_value
            Forming or temporary value to include in the preview.

        Returns
        -------
        float | None
            Previewed rolling mean, or ``None`` when insufficient committed
            values are available.
        """
        preview = self.preview_sum(current_value)

        if preview is None:
            return None

        return preview / self.size


class RollingStats:
    """
    Maintain rolling mean, variance, and standard deviation.

    The helper stores the rolling sum and squared-value sum, allowing
    fixed-window statistics to be calculated without scanning the entire
    window on every update.

    Parameters
    ----------
    size
        Number of committed observations in the rolling window.

    Raises
    ------
    ValueError
        Raised when ``size`` is not greater than zero.

    Notes
    -----
    Preview methods calculate statistics using a forming observation without
    modifying committed state.
    """

    __slots__ = ("size", "_values", "_total", "_total_sq")

    def __init__(self, size: int) -> None:
        """
        Initialize a rolling-statistics window.

        Parameters
        ----------
        size
            Number of observations in the rolling window.

        Raises
        ------
        ValueError
            Raised when ``size`` is not greater than zero.
        """
        if size <= 0:
            raise ValueError("size must be greater than 0")

        self.size = size
        self._values: deque[float] = deque()
        self._total = 0.0
        self._total_sq = 0.0

    def reset(self) -> None:
        """
        Clear all committed values and accumulated statistics.
        """
        self._values.clear()
        self._total = 0.0
        self._total_sq = 0.0

    @property
    def ready(self) -> bool:
        """
        Indicate whether the rolling window is full.

        Returns
        -------
        bool
            ``True`` when the number of committed values equals ``size``;
            otherwise ``False``.
        """
        return len(self._values) == self.size

    @property
    def count(self) -> int:
        """
        Return the number of committed values.

        Returns
        -------
        int
            Current number of values in the rolling window.
        """
        return len(self._values)

    def push(self, value: Number) -> None:
        """
        Commit a value to the rolling window.

        Parameters
        ----------
        value
            Numeric value to commit.
        """
        value = _to_float(value)

        if len(self._values) == self.size:
            oldest = self._values.popleft()
            self._total -= oldest
            self._total_sq -= oldest * oldest

        self._values.append(value)
        self._total += value
        self._total_sq += value * value

    def mean(self) -> float | None:
        """
        Return the committed rolling mean.

        Returns
        -------
        float | None
            Rolling mean when the window is full, or ``None`` while the
            window is still warming up.
        """
        if not self.ready:
            return None

        return self._total / self.size

    def variance(self, *, sample: bool = False) -> float | None:
        """
        Return the committed rolling variance.

        Parameters
        ----------
        sample
            When ``True``, calculate sample variance using Bessel's
            correction. When ``False``, calculate population variance.

        Returns
        -------
        float | None
            Rolling variance when the window is full, or ``None`` while the
            window is still warming up.
        """
        if not self.ready:
            return None

        mean = self._total / self.size
        variance = self._total_sq / self.size - mean * mean

        # Protect against tiny negative values caused by floating-point error.
        variance = max(variance, 0.0)

        if sample:
            if self.size <= 1:
                return 0.0

            variance *= self.size / (self.size - 1)

        return variance

    def std(self, *, sample: bool = False) -> float | None:
        """
        Return the committed rolling standard deviation.

        Parameters
        ----------
        sample
            When ``True``, use sample variance. When ``False``, use population
            variance.

        Returns
        -------
        float | None
            Rolling standard deviation when the window is full, or ``None``
            while the window is still warming up.
        """
        variance = self.variance(sample=sample)

        if variance is None:
            return None

        return sqrt(variance)

    def _preview_totals(
        self,
        current_value: Number,
    ) -> tuple[float, float] | None:
        """
        Calculate previewed sum and squared-value sum.

        Parameters
        ----------
        current_value
            Forming or temporary value to include.

        Returns
        -------
        tuple[float, float] | None
            Previewed sum and squared-value sum, or ``None`` when insufficient
            committed values are available.
        """
        current_value = _to_float(current_value)

        if self.size == 1:
            return current_value, current_value * current_value

        if len(self._values) < self.size - 1:
            return None

        if len(self._values) == self.size:
            oldest = self._values[0]
            total = self._total - oldest + current_value
            total_sq = (
                self._total_sq
                - oldest * oldest
                + current_value * current_value
            )
            return total, total_sq

        total = self._total + current_value
        total_sq = self._total_sq + current_value * current_value
        return total, total_sq

    def preview_mean(self, current_value: Number) -> float | None:
        """
        Preview the rolling mean using a temporary current value.

        Parameters
        ----------
        current_value
            Forming or temporary value to include.

        Returns
        -------
        float | None
            Previewed rolling mean, or ``None`` when insufficient committed
            values are available.
        """
        totals = self._preview_totals(current_value)

        if totals is None:
            return None

        total, _ = totals
        return total / self.size

    def preview_variance(
        self,
        current_value: Number,
        *,
        sample: bool = False,
    ) -> float | None:
        """
        Preview rolling variance using a temporary current value.

        Parameters
        ----------
        current_value
            Forming or temporary value to include.
        sample
            When ``True``, calculate sample variance. When ``False``,
            calculate population variance.

        Returns
        -------
        float | None
            Previewed variance, or ``None`` when insufficient committed values
            are available.
        """
        totals = self._preview_totals(current_value)

        if totals is None:
            return None

        total, total_sq = totals

        mean = total / self.size
        variance = total_sq / self.size - mean * mean
        variance = max(variance, 0.0)

        if sample:
            if self.size <= 1:
                return 0.0

            variance *= self.size / (self.size - 1)

        return variance

    def preview_std(
        self,
        current_value: Number,
        *,
        sample: bool = False,
    ) -> float | None:
        """
        Preview rolling standard deviation using a temporary current value.

        Parameters
        ----------
        current_value
            Forming or temporary value to include.
        sample
            When ``True``, use sample variance. When ``False``, use population
            variance.

        Returns
        -------
        float | None
            Previewed standard deviation, or ``None`` when insufficient
            committed values are available.
        """
        variance = self.preview_variance(
            current_value,
            sample=sample,
        )

        if variance is None:
            return None

        return sqrt(variance)


class _RollingExtreme:
    """
    Maintain a fixed-window rolling maximum or minimum.

    Candidate values are stored in a monotonic deque, providing amortized
    constant-time committed updates. Subclasses define whether a greater or
    smaller value is considered better.

    Parameters
    ----------
    size
        Number of committed observations in the rolling window.

    Raises
    ------
    ValueError
        Raised when ``size`` is not greater than zero.
    """

    __slots__ = ("size", "_values", "_candidates", "_index")

    def __init__(self, size: int) -> None:
        """
        Initialize a rolling-extreme window.

        Parameters
        ----------
        size
            Number of observations in the rolling window.

        Raises
        ------
        ValueError
            Raised when ``size`` is not greater than zero.
        """
        if size <= 0:
            raise ValueError("size must be greater than 0")

        self.size = size
        self._values: deque[tuple[int, float]] = deque()
        self._candidates: deque[tuple[int, float]] = deque()
        self._index = 0

    def reset(self) -> None:
        """
        Clear all committed values and candidate state.
        """
        self._values.clear()
        self._candidates.clear()
        self._index = 0

    @property
    def ready(self) -> bool:
        """
        Indicate whether the rolling window is full.

        Returns
        -------
        bool
            ``True`` when the number of committed values equals ``size``;
            otherwise ``False``.
        """
        return len(self._values) == self.size

    @property
    def count(self) -> int:
        """
        Return the number of committed values.

        Returns
        -------
        int
            Current number of values in the rolling window.
        """
        return len(self._values)

    def _better(self, left: float, right: float) -> bool:
        """
        Determine whether ``left`` should replace ``right`` as a candidate.

        Parameters
        ----------
        left
            New candidate value.
        right
            Existing candidate value.

        Returns
        -------
        bool
            ``True`` when ``left`` is a better extreme candidate.

        Raises
        ------
        NotImplementedError
            Raised when the subclass does not implement the comparison.
        """
        raise NotImplementedError

    def push(self, value: Number) -> float | None:
        """
        Commit a value and return the current rolling extreme.

        Parameters
        ----------
        value
            Numeric value to commit.

        Returns
        -------
        float | None
            Rolling maximum or minimum when the window is full, or ``None``
            while the window is still warming up.
        """
        value = _to_float(value)

        idx = self._index
        self._index += 1

        self._values.append((idx, value))

        while self._candidates and self._better(
            value,
            self._candidates[-1][1],
        ):
            self._candidates.pop()

        self._candidates.append((idx, value))

        expire_before = self._index - self.size

        while self._values and self._values[0][0] < expire_before:
            self._values.popleft()

        while self._candidates and self._candidates[0][0] < expire_before:
            self._candidates.popleft()

        return self.value()

    def value(self) -> float | None:
        """
        Return the current committed rolling extreme.

        Returns
        -------
        float | None
            Current rolling maximum or minimum when the window is full, or
            ``None`` while the window is still warming up.
        """
        if not self.ready:
            return None

        return self._candidates[0][1]

    def preview_value(self, current_value: Number) -> float | None:
        """
        Preview the extreme using a temporary current value.

        The preview combines the latest ``size - 1`` committed values with
        ``current_value`` without modifying committed state.

        Parameters
        ----------
        current_value
            Forming or temporary value to include.

        Returns
        -------
        float | None
            Previewed maximum or minimum, or ``None`` when insufficient
            committed values are available.
        """
        current_value = _to_float(current_value)

        if self.size == 1:
            return current_value

        if len(self._values) < self.size - 1:
            return None

        start_idx = self._index - (self.size - 1)

        candidate_value: float | None = None

        for idx, value in self._candidates:
            if idx >= start_idx:
                candidate_value = value
                break

        if candidate_value is None:
            return current_value

        if self._better(current_value, candidate_value):
            return current_value

        return candidate_value


class RollingMax(_RollingExtreme):
    """
    Maintain a fixed-window rolling maximum.
    """

    def _better(self, left: float, right: float) -> bool:
        """
        Determine whether ``left`` is a better maximum candidate.

        Parameters
        ----------
        left
            New candidate value.
        right
            Existing candidate value.

        Returns
        -------
        bool
            ``True`` when ``left`` is greater than or equal to ``right``.
        """
        return left >= right


class RollingMin(_RollingExtreme):
    """
    Maintain a fixed-window rolling minimum.
    """

    def _better(self, left: float, right: float) -> bool:
        """
        Determine whether ``left`` is a better minimum candidate.

        Parameters
        ----------
        left
            New candidate value.
        right
            Existing candidate value.

        Returns
        -------
        bool
            ``True`` when ``left`` is less than or equal to ``right``.
        """
        return left <= right


class EMAState:
    """
    Maintain state for an exponential moving average.

    The first ``period`` committed values seed the EMA using a simple moving
    average. Later values are processed recursively using ``alpha``.

    Parameters
    ----------
    period
        Number of observations used to seed the EMA.
    alpha
        Optional smoothing factor. When omitted, ``2 / (period + 1)`` is used.

    Raises
    ------
    ValueError
        Raised when ``period`` is less than one.

    Notes
    -----
    ``update()`` commits a completed value. ``preview()`` calculates a
    temporary EMA value without modifying committed state.
    """

    __slots__ = (
        "period",
        "alpha",
        "_seed_sum",
        "_seed_count",
        "_value",
    )

    def __init__(
        self,
        period: int,
        *,
        alpha: float | None = None,
    ) -> None:
        """
        Initialize EMA calculation state.

        Parameters
        ----------
        period
            Number of observations used for initial SMA seeding.
        alpha
            Optional smoothing factor.

        Raises
        ------
        ValueError
            Raised when ``period`` is less than one.
        """
        if period < 1:
            raise ValueError("EMA period must be greater than 0")

        self.period = period
        self.alpha = alpha if alpha is not None else 2.0 / (period + 1.0)

        self._seed_sum = 0.0
        self._seed_count = 0
        self._value: float | None = None

    @property
    def ready(self) -> bool:
        """
        Indicate whether the EMA has completed its seed period.

        Returns
        -------
        bool
            ``True`` when a valid EMA value is available.
        """
        return self._value is not None

    @property
    def value(self) -> float | None:
        """
        Return the current committed EMA value.

        Returns
        -------
        float | None
            Current EMA value, or ``None`` while the seed period is incomplete.
        """
        return self._value

    def reset(self) -> None:
        """
        Clear the EMA seed and committed value.
        """
        self._seed_sum = 0.0
        self._seed_count = 0
        self._value = None

    def update(self, value: Number) -> float | None:
        """
        Commit a completed value to the EMA.

        The first ``period`` values seed the EMA with a simple moving average.
        Later values update it recursively.

        Parameters
        ----------
        value
            Completed numeric observation.

        Returns
        -------
        float | None
            Updated EMA value, or ``None`` while the seed period is incomplete.
        """
        value = _to_float(value)

        if self._value is None:
            self._seed_sum += value
            self._seed_count += 1

            if self._seed_count < self.period:
                return None

            self._value = self._seed_sum / self.period
            return self._value

        self._value = (
            self.alpha * value
            + (1.0 - self.alpha) * self._value
        )

        return self._value

    def preview(self, value: Number) -> float | None:
        """
        Preview the next EMA value without modifying committed state.

        Parameters
        ----------
        value
            Forming or temporary numeric observation.

        Returns
        -------
        float | None
            Previewed EMA value, or ``None`` when insufficient seed values are
            available.
        """
        value = _to_float(value)

        if self._value is not None:
            return (
                self.alpha * value
                + (1.0 - self.alpha) * self._value
            )

        if self._seed_count == self.period - 1:
            return (self._seed_sum + value) / self.period

        return None


class WilderSmoothing:
    """
    Maintain Wilder's smoothed moving average.

    The first ``period`` committed values seed the calculation with a simple
    average. Later values use the following recursive formula:

    ``next = (previous * (period - 1) + value) / period``

    Parameters
    ----------
    period
        Number of observations used for smoothing and initial seeding.

    Raises
    ------
    ValueError
        Raised when ``period`` is not greater than zero.

    Notes
    -----
    Wilder smoothing is commonly used by ATR, RSI, ADX, and DMI indicators.
    """

    __slots__ = (
        "period",
        "_seed_sum",
        "_seed_count",
        "_value",
    )

    def __init__(self, period: int) -> None:
        """
        Initialize Wilder smoothing state.

        Parameters
        ----------
        period
            Number of observations used for smoothing.

        Raises
        ------
        ValueError
            Raised when ``period`` is not greater than zero.
        """
        if period <= 0:
            raise ValueError("period must be greater than 0")

        self.period = period
        self._seed_sum = 0.0
        self._seed_count = 0
        self._value: float | None = None

    def reset(self) -> None:
        """
        Clear the smoothing seed and committed value.
        """
        self._seed_sum = 0.0
        self._seed_count = 0
        self._value = None

    @property
    def ready(self) -> bool:
        """
        Indicate whether the smoothing seed is complete.

        Returns
        -------
        bool
            ``True`` when a smoothed value is available.
        """
        return self._value is not None

    @property
    def value(self) -> float | None:
        """
        Return the current committed smoothed value.

        Returns
        -------
        float | None
            Current smoothed value, or ``None`` while seeding is incomplete.
        """
        return self._value

    def update(self, value: Number) -> float | None:
        """
        Commit a completed value to the smoothing state.

        Parameters
        ----------
        value
            Completed numeric observation.

        Returns
        -------
        float | None
            Updated smoothed value, or ``None`` while seeding is incomplete.
        """
        value = _to_float(value)

        if self._value is None:
            self._seed_sum += value
            self._seed_count += 1

            if self._seed_count < self.period:
                return None

            self._value = self._seed_sum / self.period
            return self._value

        self._value = (
            self._value * (self.period - 1)
            + value
        ) / self.period

        return self._value

    def preview(self, current_value: Number) -> float | None:
        """
        Preview the next smoothed value without modifying committed state.

        Parameters
        ----------
        current_value
            Forming or temporary numeric observation.

        Returns
        -------
        float | None
            Previewed smoothed value, or ``None`` when insufficient seed
            values are available.
        """
        current_value = _to_float(current_value)

        if self._value is not None:
            return (
                self._value * (self.period - 1)
                + current_value
            ) / self.period

        if self._seed_count == self.period - 1:
            return (self._seed_sum + current_value) / self.period

        return None


class RollingVWAP:
    """
    Maintain cumulative or fixed-window volume-weighted average price.

    When ``size`` is ``None``, the helper calculates cumulative VWAP from all
    committed values since the last reset. When ``size`` is an integer, it
    calculates VWAP over the most recent fixed-size window.

    Parameters
    ----------
    size
        Number of observations in the rolling window, or ``None`` for
        cumulative VWAP.

    Raises
    ------
    ValueError
        Raised when ``size`` is provided but is not greater than zero.
    """

    __slots__ = (
        "size",
        "_values",
        "_pv_sum",
        "_volume_sum",
    )

    def __init__(self, size: int | None = None) -> None:
        """
        Initialize cumulative or rolling VWAP state.

        Parameters
        ----------
        size
            Number of observations in the rolling window, or ``None`` for
            cumulative VWAP.

        Raises
        ------
        ValueError
            Raised when ``size`` is provided but is not greater than zero.
        """
        if size is not None and size <= 0:
            raise ValueError("size must be greater than 0")

        self.size = size
        self._values: deque[tuple[float, float]] = deque()
        self._pv_sum = 0.0
        self._volume_sum = 0.0

    def reset(self) -> None:
        """
        Clear all committed price-volume values.
        """
        self._values.clear()
        self._pv_sum = 0.0
        self._volume_sum = 0.0

    @property
    def ready(self) -> bool:
        """
        Indicate whether a valid VWAP value is available.

        Returns
        -------
        bool
            For cumulative VWAP, ``True`` when total volume is positive. For
            rolling VWAP, ``True`` when the window is full and total volume is
            positive.
        """
        if self.size is None:
            return self._volume_sum > 0.0

        return len(self._values) == self.size and self._volume_sum > 0.0

    def push(
        self,
        price: Number,
        volume: Number,
    ) -> float | None:
        """
        Commit a price and volume observation.

        Parameters
        ----------
        price
            Price associated with the observation.
        volume
            Volume associated with the observation.

        Returns
        -------
        float | None
            Updated VWAP, or ``None`` when the rolling window is incomplete or
            total volume is zero.
        """
        price = _to_float(price)
        volume = _to_float(volume)

        pv = price * volume

        if self.size is not None and len(self._values) == self.size:
            old_pv, old_volume = self._values.popleft()
            self._pv_sum -= old_pv
            self._volume_sum -= old_volume

        self._values.append((pv, volume))
        self._pv_sum += pv
        self._volume_sum += volume

        return self.vwap()

    def vwap(self) -> float | None:
        """
        Return the current committed VWAP.

        Returns
        -------
        float | None
            Current volume-weighted average price, or ``None`` when insufficient
            data or zero total volume prevents calculation.
        """
        if not self.ready:
            return None

        if self._volume_sum == 0.0:
            return None

        return self._pv_sum / self._volume_sum

    def preview_vwap(
        self,
        current_price: Number,
        current_volume: Number,
    ) -> float | None:
        """
        Preview VWAP using a temporary price-volume observation.

        Committed state is not modified.

        Parameters
        ----------
        current_price
            Forming or temporary price.
        current_volume
            Forming or temporary volume.

        Returns
        -------
        float | None
            Previewed VWAP, or ``None`` when insufficient data or zero total
            volume prevents calculation.
        """
        current_price = _to_float(current_price)
        current_volume = _to_float(current_volume)

        current_pv = current_price * current_volume

        if self.size is None:
            volume_sum = self._volume_sum + current_volume

            if volume_sum == 0.0:
                return None

            return (self._pv_sum + current_pv) / volume_sum

        if self.size == 1:
            if current_volume == 0.0:
                return None

            return current_price

        if len(self._values) < self.size - 1:
            return None

        pv_sum = self._pv_sum
        volume_sum = self._volume_sum

        if len(self._values) == self.size:
            old_pv, old_volume = self._values[0]
            pv_sum -= old_pv
            volume_sum -= old_volume

        pv_sum += current_pv
        volume_sum += current_volume

        if volume_sum == 0.0:
            return None

        return pv_sum / volume_sum


def typical_price(
    high: Number,
    low: Number,
    close: Number,
) -> float:
    """
    Calculate the typical price.

    The typical price is calculated as:

    ``(high + low + close) / 3``

    Parameters
    ----------
    high
        Highest price of the observation.
    low
        Lowest price of the observation.
    close
        Closing price of the observation.

    Returns
    -------
    float
        Calculated typical price.
    """
    return (
        _to_float(high)
        + _to_float(low)
        + _to_float(close)
    ) / 3.0


def weighted_price(
    high: Number,
    low: Number,
    close: Number,
) -> float:
    """
    Calculate the weighted closing price.

    The closing price receives twice the weight of the high and low prices:

    ``(high + low + 2 * close) / 4``

    Parameters
    ----------
    high
        Highest price of the observation.
    low
        Lowest price of the observation.
    close
        Closing price of the observation.

    Returns
    -------
    float
        Calculated weighted closing price.
    """
    return (
        _to_float(high)
        + _to_float(low)
        + _to_float(close)
        + _to_float(close)
    ) / 4.0


def median_price(
    high: Number,
    low: Number,
) -> float:
    """
    Calculate the median price.

    The median price is calculated as:

    ``(high + low) / 2``

    Parameters
    ----------
    high
        Highest price of the observation.
    low
        Lowest price of the observation.

    Returns
    -------
    float
        Midpoint between the high and low prices.
    """
    return (
        _to_float(high)
        + _to_float(low)
    ) / 2.0


def true_range(
    high: Number,
    low: Number,
    previous_close: Number,
) -> float:
    """
    Calculate the true range of a price observation.

    True range is the greatest of:

    - ``high - low``
    - ``abs(high - previous_close)``
    - ``abs(low - previous_close)``

    Parameters
    ----------
    high
        Highest price of the current observation.
    low
        Lowest price of the current observation.
    previous_close
        Closing price of the preceding observation.

    Returns
    -------
    float
        Calculated true range.
    """
    high = _to_float(high)
    low = _to_float(low)
    previous_close = _to_float(previous_close)

    return max(
        high - low,
        abs(high - previous_close),
        abs(low - previous_close),
    )


def empty_indicator_result(
    prices: np.ndarray,
) -> np.ndarray | None:
    """
    Create an empty indicator result matching the input layout.

    A one-dimensional input represents a single symbol and returns ``None``.
    A multidimensional input returns one ``NaN`` value for each symbol in the
    second dimension.

    Parameters
    ----------
    prices
        One-dimensional or multidimensional input price array.

    Returns
    -------
    numpy.ndarray | None
        One-dimensional ``NaN`` array with length ``prices.shape[1]`` for
        multidimensional input, or ``None`` for one-dimensional input.
    """
    if prices.ndim == 1:
        return None

    return np.full(
        shape=(prices.shape[1],),
        fill_value=np.nan,
        dtype=float,
    )