from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from application.context.logging_context import RuntimeLoggingContext


class SymbolCheckReason(StrEnum):
    INVALID_SYMBOL_FORMAT = "INVALID_SYMBOL_FORMAT"
    UNKNOWN_SYMBOL = "UNKNOWN_SYMBOL"

    DATA_PROVIDER_NOT_SUPPORTED = "DATA_PROVIDER_NOT_SUPPORTED"
    DATA_PROVIDER_SYMBOL_INACTIVE = "DATA_PROVIDER_SYMBOL_INACTIVE"
    DATA_NOT_AVAILABLE = "DATA_NOT_AVAILABLE"

    BROKER_NOT_SUPPORTED = "BROKER_NOT_SUPPORTED"
    BROKER_SYMBOL_INACTIVE = "BROKER_SYMBOL_INACTIVE"
    BROKER_NOT_TRADABLE = "BROKER_NOT_TRADABLE"


@dataclass(frozen=True, slots=True)
class SymbolCheckResult:
    symbol: str
    valid: bool

    instrument_id: int | None = None
    name: str | None = None
    asset_class: str | None = None
    currency: str | None = None
    primary_exchange: str | None = None

    data_provider: str | None = None
    provider_symbol: str | None = None
    provider_active: bool = False
    reference_available: bool = False
    current_data_available: bool = False

    broker: str | None = None
    broker_asset_id: str | None = None
    broker_symbol: str | None = None
    broker_exchange: str | None = None
    broker_status: str | None = None

    tradable: bool = False
    marginable: bool = False
    shortable: bool = False
    easy_to_borrow: bool = False
    fractionable: bool = False
    borrow_status: str | None = None

    reason: SymbolCheckReason | None = None
    message: str | None = None


class SymbolReferenceService:
    """
    Per-strategy-worker symbol registry.

    The SQLite connection is opened once.

    Only symbols actually used by the strategy are loaded into
    the in-process cache.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        data_provider: str,
        broker: str,
        logger: RuntimeLoggingContext
    ) -> None:
        self._database_path = Path(database_path).resolve()

        if not self._database_path.exists():
            self._logger.platform_error(
                message="SQLite DB doesn't exist",
                path= self._database_path
            )
            raise FileNotFoundError(
                f"Symbol registry was not found: "
                f"{self._database_path}"
            )

        self._data_provider = self._normalize_source_name(
            data_provider,
            field_name="data_provider",
        )

        self._broker = self._normalize_source_name(
            broker,
            field_name="broker",
        )

        self._logger = logger
        self._lock = threading.RLock()

        self._connection = sqlite3.connect(
            (
                f"file:{self._database_path}"
                "?mode=ro"
                "&immutable=1"
            ),
            uri=True,
            check_same_thread=False,
        )

        self._connection.row_factory = sqlite3.Row

        self._connection.execute(
            "PRAGMA query_only = ON"
        )

        # Limit SQLite's private cache for each worker process.
        self._connection.execute(
            "PRAGMA cache_size = -256"
        )

        self._validate_schema()

        # Only symbols used by this strategy worker are cached.
        self._registered: dict[
            str,
            SymbolCheckResult,
        ] = {}

    @property
    def data_provider(self) -> str:
        return self._data_provider

    @property
    def broker(self) -> str:
        return self._broker

    def register(
        self,
        symbol: str,
    ) -> SymbolCheckResult:
        """
        Load and cache one symbol.

        The first registration queries SQLite. Repeated registrations
        of the same symbol return the cached result.
        """
        with self._lock:
            return self._register_locked(symbol)

    def _register_locked(self, symbol: str) -> SymbolCheckResult:
        normalized_symbol = self._normalize_symbol(symbol)

        if normalized_symbol is None:
            return SymbolCheckResult(
                symbol=str(symbol),
                valid=False,
                data_provider=self._data_provider,
                broker=self._broker,
                reason=SymbolCheckReason.INVALID_SYMBOL_FORMAT,
                message="Symbol must be a non-empty string.",
            )

        cached = self._registered.get(normalized_symbol)

        if cached is not None:
            return cached

        result = self._load_symbol(
            normalized_symbol
        )

        # Cache valid and invalid results. This prevents repeated
        # SQLite queries for an unsupported symbol.
        self._registered[normalized_symbol] = result

        return result

    def get(
        self,
        symbol: str,
    ) -> SymbolCheckResult | None:
        """
        Return an already-registered symbol without querying SQLite.
        """
        normalized_symbol = self._normalize_symbol(symbol)

        if normalized_symbol is None:
            return None

        with self._lock:
            return self._registered.get(
                normalized_symbol
            )

    def check(
        self,
        symbol: str,
    ) -> SymbolCheckResult:
        """
        Return the cached result, registering the symbol if necessary.
        """
        return self.register(symbol)

    def is_registered(
        self,
        symbol: str,
    ) -> bool:
        normalized_symbol = self._normalize_symbol(symbol)

        if normalized_symbol is None:
            return False

        with self._lock:
            return normalized_symbol in self._registered

    def is_tradable(
        self,
        symbol: str,
    ) -> bool:
        return self.register(symbol).valid

    def instrument_id(
        self,
        symbol: str,
    ) -> int | None:
        return self.register(symbol).instrument_id

    def unregister(
        self,
        symbol: str,
    ) -> bool:
        """
        Remove one symbol from the worker-local cache.

        This does not modify the SQLite registry.
        """
        normalized_symbol = self._normalize_symbol(symbol)

        if normalized_symbol is None:
            return False

        with self._lock:
            return (
                self._registered.pop(
                    normalized_symbol,
                    None,
                )
                is not None
            )

    def clear(self) -> None:
        """
        Clear all worker-local symbol information.
        """
        with self._lock:
            self._registered.clear()

    def close(self) -> None:
        with self._lock:
            self._registered.clear()
            self._connection.close()

    def __enter__(self) -> SymbolReferenceService:
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()

    def _load_symbol(
        self,
        symbol: str,
    ) -> SymbolCheckResult:
        row = self._connection.execute(
            """
            SELECT
                i.instrument_id,
                i.symbol,
                i.name,
                i.asset_class,
                i.currency,
                i.primary_exchange,

                p.provider,
                p.provider_symbol,
                p.active AS provider_active,
                p.reference_available,
                p.current_data_available,

                b.broker,
                b.broker_asset_id,
                b.broker_symbol,
                b.broker_exchange,
                b.status AS broker_status,
                b.tradable,
                b.marginable,
                b.shortable,
                b.easy_to_borrow,
                b.fractionable,
                b.borrow_status

            FROM instruments AS i

            LEFT JOIN data_provider_symbols AS p
                ON p.instrument_id = i.instrument_id
               AND p.provider = ?

            LEFT JOIN broker_symbols AS b
                ON b.instrument_id = i.instrument_id
               AND b.broker = ?

            WHERE i.symbol = ?

            LIMIT 1
            """,
            (
                self._data_provider,
                self._broker,
                symbol,
            ),
        ).fetchone()

        if row is None:
            return SymbolCheckResult(
                symbol=symbol,
                valid=False,
                data_provider=self._data_provider,
                broker=self._broker,
                reason=SymbolCheckReason.UNKNOWN_SYMBOL,
                message=(
                    f"{symbol} is not recognized "
                    "by the platform."
                ),
            )

        common = self._build_common_fields(row)

        if row["provider"] is None:
            return SymbolCheckResult(
                **common,
                valid=False,
                reason=(
                    SymbolCheckReason
                    .DATA_PROVIDER_NOT_SUPPORTED
                ),
                message=(
                    f"{self._data_provider} does not "
                    f"support {symbol}."
                ),
            )

        if not common["provider_active"]:
            return SymbolCheckResult(
                **common,
                valid=False,
                reason=(
                    SymbolCheckReason
                    .DATA_PROVIDER_SYMBOL_INACTIVE
                ),
                message=(
                    f"{symbol} is inactive on "
                    f"{self._data_provider}."
                ),
            )

        if not common["current_data_available"]:
            return SymbolCheckResult(
                **common,
                valid=False,
                reason=SymbolCheckReason.DATA_NOT_AVAILABLE,
                message=(
                    f"Current market data for {symbol} "
                    f"is not available from "
                    f"{self._data_provider}."
                ),
            )

        if row["broker"] is None:
            return SymbolCheckResult(
                **common,
                valid=False,
                reason=SymbolCheckReason.BROKER_NOT_SUPPORTED,
                message=(
                    f"{self._broker} does not support "
                    f"{symbol}."
                ),
            )

        broker_status = self._normalize_status(
            row["broker_status"]
        )

        if broker_status != "active":
            return SymbolCheckResult(
                **common,
                valid=False,
                reason=(
                    SymbolCheckReason
                    .BROKER_SYMBOL_INACTIVE
                ),
                message=(
                    f"{symbol} is not active on "
                    f"{self._broker}."
                ),
            )

        if not common["tradable"]:
            return SymbolCheckResult(
                **common,
                valid=False,
                reason=SymbolCheckReason.BROKER_NOT_TRADABLE,
                message=(
                    f"{symbol} is active on "
                    f"{self._broker}, but it is not "
                    "currently tradable."
                ),
            )

        return SymbolCheckResult(
            **common,
            valid=True,
        )

    def _build_common_fields(
        self,
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        return {
            "symbol": str(row["symbol"]),
            "instrument_id": int(row["instrument_id"]),
            "name": row["name"],
            "asset_class": row["asset_class"],
            "currency": row["currency"],
            "primary_exchange": row["primary_exchange"],

            "data_provider": self._data_provider,
            "provider_symbol": row["provider_symbol"],
            "provider_active": self._to_bool(
                row["provider_active"]
            ),
            "reference_available": self._to_bool(
                row["reference_available"]
            ),
            "current_data_available": self._to_bool(
                row["current_data_available"]
            ),

            "broker": self._broker,
            "broker_asset_id": row["broker_asset_id"],
            "broker_symbol": row["broker_symbol"],
            "broker_exchange": row["broker_exchange"],
            "broker_status": row["broker_status"],

            "tradable": self._to_bool(
                row["tradable"]
            ),
            "marginable": self._to_bool(
                row["marginable"]
            ),
            "shortable": self._to_bool(
                row["shortable"]
            ),
            "easy_to_borrow": self._to_bool(
                row["easy_to_borrow"]
            ),
            "fractionable": self._to_bool(
                row["fractionable"]
            ),
            "borrow_status": row["borrow_status"],
        }

    def _validate_schema(self) -> None:
        required_tables = {
            "instruments",
            "data_provider_symbols",
            "broker_symbols",
        }

        rows = self._connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        existing_tables = {
            str(row["name"])
            for row in rows
        }

        missing_tables = (
            required_tables - existing_tables
        )

        if missing_tables:
            raise RuntimeError(
                "Invalid symbol registry database. "
                f"Missing tables: {sorted(missing_tables)}"
            )

    @staticmethod
    def _normalize_symbol(
        symbol: object,
    ) -> str | None:
        if not isinstance(symbol, str):
            return None

        normalized = symbol.strip().upper()

        return normalized or None

    @staticmethod
    def _normalize_source_name(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string"
            )

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized

    @staticmethod
    def _normalize_status(
        value: object,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()

        return normalized or None

    @staticmethod
    def _to_bool(
        value: object,
    ) -> bool:
        if value is None:
            return False

        return bool(value)
