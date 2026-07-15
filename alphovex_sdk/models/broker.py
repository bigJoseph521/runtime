from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final


@dataclass(frozen=True, slots=True)
class AssetSpec:
    """
    Define execution rules for an asset type.

    Asset specifications describe the price and quantity increments accepted
    by a broker. The platform uses these values to normalize and validate
    orders before submission.

    Attributes
    ----------
    price_tick
        Smallest supported price increment.
    qty_step
        Smallest supported quantity increment.
    min_qty
        Minimum permitted order quantity.
    max_qty
        Maximum permitted order quantity, or ``None`` when the broker does
        not define an explicit maximum.
    """

    price_tick: float
    qty_step: float
    min_qty: float
    max_qty: float | None


@dataclass(frozen=True, slots=True)
class ExecutionSpec:
    """
    Define broker-specific execution rules.

    An execution specification associates each supported asset type with its
    corresponding price and quantity rules.

    Attributes
    ----------
    name
        Canonical broker name.
    asset_rules
        Read-only mapping from asset-type names to their execution rules.
    """

    name: str
    asset_rules: Mapping[str, AssetSpec]

    def get_asset_spec(self, asset_type: str) -> AssetSpec | None:
        """
        Return the execution rules for an asset type.

        Parameters
        ----------
        asset_type
            Canonical asset-type name, such as ``"stock"`` or ``"crypto"``.

        Returns
        -------
        AssetSpec | None
            Execution rules for the requested asset type, or ``None`` when the
            asset type is not supported.
        """
        return self.asset_rules.get(asset_type)

    def is_supported(self, asset_type: str) -> bool:
        """
        Determine whether the broker supports an asset type.

        Parameters
        ----------
        asset_type
            Canonical asset-type name to check.

        Returns
        -------
        bool
            ``True`` when execution rules are defined for the asset type;
            otherwise ``False``.
        """
        return asset_type in self.asset_rules


ALPACA_SPEC: Final[ExecutionSpec] = ExecutionSpec(
    name="alpaca",
    asset_rules=MappingProxyType(
        {
            "stock": AssetSpec(
                price_tick=0.01,
                qty_step=0.000000001,
                min_qty=0.000000001,
                max_qty=None,
            ),
            "crypto": AssetSpec(
                price_tick=0.0001,
                qty_step=0.00000001,
                min_qty=0.00000001,
                max_qty=None,
            ),
        }
    ),
)


def get_execution_spec(
    broker_name: str,
    asset_type: str,
) -> AssetSpec | None:
    """
    Return broker execution rules for an asset type.

    Parameters
    ----------
    broker_name
        Canonical broker name.
    asset_type
        Canonical asset-type name, such as ``"stock"`` or ``"crypto"``.

    Returns
    -------
    AssetSpec | None
        Matching execution rules, or ``None`` when the broker or asset type
        is not supported.

    Examples
    --------
    ```python
    stock_spec = get_execution_spec(
        broker_name="alpaca",
        asset_type="stock",
    )

    if stock_spec is not None:
        print(stock_spec.price_tick)
    ```
    """
    if broker_name == ALPACA_SPEC.name:
        return ALPACA_SPEC.get_asset_spec(asset_type)

    return None