from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

import httpx
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from nats.aio.subscription import Subscription

from alphovex_sdk.typedefs.aliases import Symbol, Timeframe
from application.context.logging_context import RuntimeLoggingContext
from application.event_handling.events_model import ExternalEventType
from application.event_handling.external_event_bus import ExternalEventBus
from application.ports.market_data import MarketDataPort
from infrastructure.config.config import RuntimeConfig
from infrastructure.nats.helpers import (
    from_raw_1m_bar_to_bar,
    from_raw_1m_bar_to_tick,
    from_raw_custom_bar_to_bar,
    from_raw_quote_to_quote,
)


class NATSMarketDataClient(MarketDataPort):
    """Dynamic, symbol-specific Core NATS market-data consumer."""

    def __init__(
        self,
        event_bus: ExternalEventBus,
        logger: RuntimeLoggingContext,
        config: RuntimeConfig,
        client_name: str = "swr-market-data-client",
    ) -> None:
        self._event_bus = event_bus
        self._logger = logger
        self._server_url = config.NATS_server_url
        self._subject_prefix = config.NATS_subject_prefix
        self._timeframe_service_url = config.timeframe_service_base_url.rstrip("/")
        self._client_name = client_name

        self._client = NATSClient()
        self._http = httpx.AsyncClient(timeout=config.http_timeout, trust_env=False)
        self._subscriptions: dict[str, Subscription] = {}
        self._targets: set[tuple[Symbol, Timeframe]] = set()
        self._leases: dict[tuple[Symbol, Timeframe], str] = {}
        self._lock = asyncio.Lock()
        self._started = False
        self._lease_task: asyncio.Task[None] | None = None

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    @property
    def targets(self) -> frozenset[tuple[Symbol, Timeframe]]:
        return frozenset(self._targets)

    @staticmethod
    def _normalize(symbol: Symbol, timeframe: Timeframe) -> tuple[Symbol, Timeframe]:
        normalized_symbol = str(symbol).strip().upper()
        normalized_timeframe = str(timeframe).strip().lower()
        if not normalized_symbol:
            raise ValueError("symbol is required")
        if normalized_timeframe not in {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}:
            raise ValueError(f"unsupported timeframe: {timeframe}")
        return normalized_symbol, normalized_timeframe  # type: ignore[return-value]

    def _desired_subjects(self, targets: set[tuple[Symbol, Timeframe]]) -> set[str]:
        subjects: set[str] = set()
        symbols = {symbol for symbol, _ in targets}
        for symbol in symbols:
            subjects.add(f"{self._subject_prefix}.{symbol}.bar")
            subjects.add(f"{self._subject_prefix}.{symbol}.quote")
        for symbol, timeframe in targets:
            if timeframe != "1m":
                subjects.add(f"{self._subject_prefix}.{symbol}.bar.{timeframe}")
        return subjects

    async def start(self) -> None:
        async with self._lock:
            if self._started and self._client.is_connected:
                return
            if self._client.is_closed:
                self._client = NATSClient()
            await self._client.connect(
                servers=[self._server_url],
                name=self._client_name,
                allow_reconnect=True,
                max_reconnect_attempts=-1,
                reconnect_time_wait=2,
                ping_interval=20,
                max_outstanding_pings=3,
                error_cb=self._on_error,
                disconnected_cb=self._on_disconnected,
                reconnected_cb=self._on_reconnected,
                closed_cb=self._on_closed,
            )
            self._started = True
            await self._sync_subscriptions_locked()
            self._lease_task = asyncio.create_task(
                self._renew_leases_loop(),
                name="timeframe-lease-renewer",
            )
            self._logger.platform_info(message=f"Connected to NATS server: {self._server_url}")

    async def restart(self) -> None:
        targets = list(self._targets)
        await self.stop(close_http=False)
        await self.start()
        await self.set_channels(targets)

    async def stop(self, close_http: bool = True) -> None:
        lease_task = self._lease_task
        self._lease_task = None
        if lease_task is not None:
            lease_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await lease_task
        async with self._lock:
            await self._unsubscribe_all_locked(release_leases=True)
            if not self._client.is_closed:
                await self._client.drain()
            self._started = False
        if close_http:
            await self._http.aclose()
        self._logger.platform_info(message="NATS market-data client stopped")

    async def set_channels(self, ref: list[tuple[Symbol, Timeframe]]) -> None:
        normalized = {self._normalize(symbol, timeframe) for symbol, timeframe in ref}
        async with self._lock:
            await self._apply_targets_locked(normalized)

    async def add_channel(self, symbol: Symbol, timeframe: Timeframe, _: Any = None) -> None:
        target = self._normalize(symbol, timeframe)
        async with self._lock:
            if target in self._targets:
                return
            await self._apply_targets_locked(self._targets | {target})

    async def remove_channel(self, symbol: Symbol, timeframe: Timeframe, _: Any = None) -> None:
        target = self._normalize(symbol, timeframe)
        async with self._lock:
            if target not in self._targets:
                return
            await self._apply_targets_locked(self._targets - {target})

    async def unsubscribe_all_channels(self) -> None:
        async with self._lock:
            await self._apply_targets_locked(set())

    async def _apply_targets_locked(self, targets: set[tuple[Symbol, Timeframe]]) -> None:
        added = targets - self._targets
        removed = self._targets - targets

        acquired: list[tuple[Symbol, Timeframe]] = []
        try:
            for target in added:
                if target[1] != "1m":
                    self._leases[target] = await self._acquire_timeframe(*target)
                    acquired.append(target)
        except Exception:
            for target in acquired:
                lease_id = self._leases.pop(target, None)
                if lease_id:
                    await self._release_timeframe(lease_id)
            raise

        self._targets = targets
        if self._started and self._client.is_connected:
            await self._sync_subscriptions_locked()

        for target in removed:
            lease_id = self._leases.pop(target, None)
            if lease_id:
                await self._release_timeframe(lease_id)

        self._logger.platform_info(
            message="NATS market-data targets updated",
            targets=sorted(self._targets),
        )

    async def _sync_subscriptions_locked(self) -> None:
        desired = self._desired_subjects(self._targets)
        current = set(self._subscriptions)

        for subject in sorted(desired - current):
            self._subscriptions[subject] = await self._client.subscribe(
                subject,
                cb=self._handle_message,
            )
            self._logger.platform_info(message=f"Subscribed to {subject}")

        for subject in sorted(current - desired):
            subscription = self._subscriptions.pop(subject)
            await subscription.unsubscribe()
            self._logger.platform_info(message=f"Unsubscribed from {subject}")

        if self._client.is_connected:
            await self._client.flush()

    async def _unsubscribe_all_locked(self, release_leases: bool) -> None:
        subscriptions = list(self._subscriptions.items())
        self._subscriptions.clear()
        for subject, subscription in subscriptions:
            try:
                await subscription.unsubscribe()
            except Exception as exc:
                self._logger.platform_warning(
                    message=f"Failed to unsubscribe from {subject}: {exc}"
                )
        if release_leases:
            leases = list(self._leases.values())
            self._leases.clear()
            self._targets.clear()
            for lease_id in leases:
                await self._release_timeframe(lease_id)

    async def _acquire_timeframe(self, symbol: Symbol, timeframe: Timeframe) -> str:
        response = await self._http.post(
            f"{self._timeframe_service_url}/v1/timeframes/acquire",
            json={
                "consumer_id": self._client_name,
                "symbol": symbol,
                "timeframe": timeframe,
            },
        )
        response.raise_for_status()
        payload = response.json()
        lease_id = payload.get("lease_id")
        if not isinstance(lease_id, str) or not lease_id:
            raise ValueError("timeframe service response is missing lease_id")
        return lease_id

    async def _release_timeframe(self, lease_id: str) -> None:
        try:
            response = await self._http.delete(
                f"{self._timeframe_service_url}/v1/timeframes/leases/{lease_id}"
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self._logger.platform_warning(
                message=f"Failed to release timeframe lease {lease_id}: {exc}"
            )

    async def _renew_leases_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            async with self._lock:
                leases = list(self._leases.items())
            for target, lease_id in leases:
                try:
                    response = await self._http.post(
                        f"{self._timeframe_service_url}/v1/timeframes/leases/{lease_id}/renew"
                    )
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    self._logger.platform_warning(
                        message=(
                            "Failed to renew timeframe lease "
                            f"{lease_id} for {target[0]} {target[1]}: {exc}"
                        )
                    )

    async def _handle_message(self, message: Msg) -> None:
        try:
            payload = json.loads(message.data.decode("utf-8"))
            if not isinstance(payload, list) or not payload:
                raise ValueError("market-data payload must be a non-empty array")

            schema = payload[0]
            if schema == 0:
                if len(payload) < 10:
                    raise ValueError("invalid custom-bar payload")
                symbol, bar = from_raw_custom_bar_to_bar(payload)
                timeframe = message.subject.rsplit(".", 1)[-1]
                self._event_bus.publish({
                    "type": ExternalEventType.CURRENT_BAR,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "payload": bar,
                    "completed": False,
                })
            elif schema == 2:
                if len(payload) < 7:
                    raise ValueError("invalid quote payload")
                symbol, quote = from_raw_quote_to_quote(payload)
                self._event_bus.publish({
                    "type": ExternalEventType.QUOTE,
                    "symbol": symbol,
                    "payload": quote,
                })
            elif schema == 3:
                if len(payload) < 12:
                    raise ValueError("invalid tick/current-bar payload")
                symbol, tick = from_raw_1m_bar_to_tick(payload)
                _, bar = from_raw_1m_bar_to_bar(payload)
                self._event_bus.publish({
                    "type": ExternalEventType.CURRENT_BAR,
                    "symbol": symbol,
                    "timeframe": "1m",
                    "payload": bar,
                    "completed": False,
                })
                self._event_bus.publish({
                    "type": ExternalEventType.TICK,
                    "symbol": symbol,
                    "payload": tick,
                })
        except Exception as exc:
            self._logger.platform_error(
                message=f"Market-data handler failed on {message.subject}: {exc}"
            )

    async def _on_error(self, error: Exception) -> None:
        self._logger.platform_error(message=f"NATS error: {error}")

    async def _on_disconnected(self) -> None:
        self._logger.platform_warning(message="NATS disconnected")

    async def _on_reconnected(self) -> None:
        self._logger.platform_info(message=f"NATS reconnected: {self._client.connected_url}")

    async def _on_closed(self) -> None:
        self._logger.platform_info(message="NATS connection closed")
