from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import grpc
import numpy as np

from alphovex_sdk import Timeframe
from application.context.logging_context import RuntimeLoggingContext
from application.ports.historical_data import HistoricalDataClientPort
from contracts.rows import _BarRow

from .generated import historical_data_pb2
from .generated import historical_data_pb2_grpc


_TIMEFRAME_DURATION: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "10m": timedelta(minutes=10),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "1w": timedelta(weeks=1),
    "1mo": timedelta(days=31),
}


class GRPCHistoricalDataClient(HistoricalDataClientPort):
    """Async adapter for historical_data.HistoricalDataService."""

    def __init__(
        self,
        target: str,
        timeout_seconds: float,
        logger: RuntimeLoggingContext,
    ) -> None:
        normalized_target = target.removeprefix("http://").removeprefix(
            "https://"
        )
        self._target = normalized_target
        self._timeout_seconds = timeout_seconds
        self._logger = logger
        self._channel = grpc.aio.insecure_channel(normalized_target)
        self._stub = historical_data_pb2_grpc.HistoricalDataServiceStub(
            self._channel
        )

    async def get_bar_history(
        self,
        symbol: str,
        timeframe: Timeframe,
        window: int,
    ) -> list[_BarRow] | None:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = str(timeframe).strip().lower()

        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if window < 1:
            raise ValueError("window must be greater than zero")

        duration = _TIMEFRAME_DURATION.get(normalized_timeframe)
        if duration is None:
            self._logger.platform_error(
                message="Historical gRPC timeframe is unsupported",
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
            )
            return None

        to_utc = datetime.now(timezone.utc)
        lookback = max(duration * (window * 3), timedelta(days=7))
        from_utc = to_utc - lookback

        try:
            response = await self._query(
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
                window=window,
                from_utc=from_utc,
                to_utc=to_utc,
            )
        except grpc.aio.AioRpcError as error:
            retry_range = self._range_retry_from_error(
                error=error,
                duration=duration,
                lookback=lookback,
                original_to_utc=to_utc,
            )
            if retry_range is None:
                self._log_rpc_error(
                    error,
                    normalized_symbol,
                    normalized_timeframe,
                )
                return None

            retry_from, retry_to = retry_range
            try:
                response = await self._query(
                    symbol=normalized_symbol,
                    timeframe=normalized_timeframe,
                    window=window,
                    from_utc=retry_from,
                    to_utc=retry_to,
                )
            except grpc.aio.AioRpcError as retry_error:
                self._log_rpc_error(
                    retry_error,
                    normalized_symbol,
                    normalized_timeframe,
                )
                return None

        # The RPC is requested in descending order. Runtime ring buffers must
        # be seeded oldest-to-newest so their public view remains newest-first.
        return [
            self._to_bar_row(bar)
            for bar in reversed(response.bars)
        ]

    async def _query(
        self,
        *,
        symbol: str,
        timeframe: str,
        window: int,
        from_utc: datetime,
        to_utc: datetime,
    ):
        request = historical_data_pb2.QueryHistoricalDataRequest(
            symbol=symbol,
            timeframe=timeframe,
            from_utc=self._format_utc(from_utc),
            to_utc=self._format_utc(to_utc),
            data_type=historical_data_pb2.HISTORICAL_DATA_TYPE_BAR,
            sort="desc",
            limit=window,
            adjusted=False,
            caller_service="strategy-worker-runtime",
        )
        return await self._stub.QueryHistoricalData(
            request,
            timeout=self._timeout_seconds,
            metadata=(("x-caller-service", "strategy-worker-runtime"),),
        )

    def _range_retry_from_error(
        self,
        *,
        error: grpc.aio.AioRpcError,
        duration: timedelta,
        lookback: timedelta,
        original_to_utc: datetime,
    ) -> tuple[datetime, datetime] | None:
        metadata = self._metadata_dict(error.trailing_metadata())
        reason = metadata.get("x-historical-range-error")
        boundary_raw = metadata.get("x-boundary-bar-open-utc")
        if not reason or not boundary_raw:
            return None

        try:
            boundary = datetime.fromisoformat(
                boundary_raw.replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError:
            return None

        if reason == "after_latest_stored":
            retry_to = boundary + duration
            return retry_to - lookback, retry_to
        if reason == "from_before_earliest_stored":
            return boundary, original_to_utc
        return None

    @staticmethod
    def _metadata_dict(metadata: Iterable | None) -> dict[str, str]:
        if metadata is None:
            return {}
        return {str(item.key): str(item.value) for item in metadata}

    @staticmethod
    def _format_utc(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )

    @staticmethod
    def _to_bar_row(raw) -> _BarRow:
        normalized = raw.time_utc.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(normalized)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        return _BarRow(
            ts=np.datetime64(timestamp, "ms"),
            open=np.float64(raw.open),
            high=np.float64(raw.high),
            low=np.float64(raw.low),
            close=np.float64(raw.close),
            volume=np.float64(raw.volume),
        )

    def _log_rpc_error(
        self,
        error: grpc.aio.AioRpcError,
        symbol: str,
        timeframe: str,
    ) -> None:
        self._logger.platform_error(
            message="Historical gRPC request failed",
            target=self._target,
            symbol=symbol,
            timeframe=timeframe,
            grpc_status=error.code().name,
            error=error.details() or str(error),
        )

    async def close(self) -> None:
        await self._channel.close()
