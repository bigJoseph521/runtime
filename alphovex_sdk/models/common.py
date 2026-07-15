from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..typedefs import CashValue


class Currency(StrEnum):
    """
    Define currency codes supported by the SDK.

    Each member uses an uppercase ISO 4217-style currency code as its string
    value.

    Members
    -------
    USD
        United States dollar.
    EUR
        Euro.
    GBP
        British pound sterling.
    JPY
        Japanese yen.
    CNY
        Chinese yuan.
    INR
        Indian rupee.
    BRL
        Brazilian real.
    MXN
        Mexican peso.
    ARS
        Argentine peso.
    COP
        Colombian peso.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"
    ARS = "ARS"
    COP = "COP"


@dataclass
class Money:
    """
    Represent a monetary amount in a single currency.

    Arithmetic operations preserve the currency of the current instance.
    Addition and subtraction require both operands to use the same currency.
    Multiplication, division, floor division, and modulo operations accept a
    numeric scalar.

    Attributes
    ----------
    amount
        Monetary value expressed in ``currency``.
    currency
        Currency in which the monetary value is denominated.
    """

    amount: CashValue
    currency: Currency

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the monetary value.

        Returns
        -------
        str
            String containing the amount and currency.
        """
        return (
            f"Money(amount={self.amount!r}, "
            f"currency={self.currency!r})"
        )

    def __add__(self, other: Money) -> Money:
        """
        Add another monetary amount.

        Parameters
        ----------
        other
            Monetary amount to add.

        Returns
        -------
        Money
            New monetary value containing the combined amount.

        Raises
        ------
        ValueError
            Raised when the two monetary values use different currencies.
        """
        if self.currency != other.currency:
            raise ValueError(
                "Cannot add money in different currencies: "
                f"{self.currency} and {other.currency}"
            )

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency,
        )

    def __sub__(self, other: Money) -> Money:
        """
        Subtract another monetary amount.

        Parameters
        ----------
        other
            Monetary amount to subtract.

        Returns
        -------
        Money
            New monetary value containing the difference.

        Raises
        ------
        ValueError
            Raised when the two monetary values use different currencies.
        """
        if self.currency != other.currency:
            raise ValueError(
                "Cannot subtract money in different currencies: "
                f"{self.currency} and {other.currency}"
            )

        return Money(
            amount=self.amount - other.amount,
            currency=self.currency,
        )

    def __mul__(self, other: float) -> Money:
        """
        Multiply the monetary amount by a scalar.

        Parameters
        ----------
        other
            Numeric multiplier.

        Returns
        -------
        Money
            New monetary value containing the multiplied amount.
        """
        return Money(
            amount=self.amount * other,
            currency=self.currency,
        )

    def __truediv__(self, other: float) -> Money:
        """
        Divide the monetary amount by a scalar.

        Parameters
        ----------
        other
            Numeric divisor.

        Returns
        -------
        Money
            New monetary value containing the divided amount.

        Raises
        ------
        ZeroDivisionError
            Raised when ``other`` is zero.
        """
        return Money(
            amount=self.amount / other,
            currency=self.currency,
        )

    def __floordiv__(self, other: float) -> Money:
        """
        Floor-divide the monetary amount by a scalar.

        Parameters
        ----------
        other
            Numeric divisor.

        Returns
        -------
        Money
            New monetary value containing the floor-divided amount.

        Raises
        ------
        ZeroDivisionError
            Raised when ``other`` is zero.
        """
        return Money(
            amount=self.amount // other,
            currency=self.currency,
        )

    def __mod__(self, other: float) -> Money:
        """
        Return the remainder after dividing the amount by a scalar.

        Parameters
        ----------
        other
            Numeric divisor.

        Returns
        -------
        Money
            New monetary value containing the remainder.

        Raises
        ------
        ZeroDivisionError
            Raised when ``other`` is zero.
        """
        return Money(
            amount=self.amount % other,
            currency=self.currency,
        )