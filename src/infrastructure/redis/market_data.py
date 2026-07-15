from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import Any
from datetime import datetime

import redis.asyncio as redis
from redis.asyncio.client import PubSub
from redis.exceptions import RedisError

from alphovex_sdk.typedefs.aliases import Symbol, Timeframe

from infrastructure.config.config import RuntimeConfig

from infrastructure.redis.helpers import (
    calculate_partition, 
    from_raw_to_quote, 
    from_raw_to_tick,
)
from application.event_handling.external_event_bus import ExternalEventBus, ExternalEventType
from application.context.logging_context import RuntimeLoggingContext
from application.ports.market_data import MarketDataPort
from contracts.rows import _QuoteRow, _TickRow

class RedisMarketDataListener(MarketDataPort):
    """
    Asynchronous Redis Pub/Sub market-data listener.

    Characteristics:

    - Uses PubSub.listen(), not polling.
    - Channels can be changed dynamically.
    - The Redis connection remains active during normal channel changes.
    - The connection is recreated after Redis/network failures.
    - The consumer waits on an asyncio.Event when no channels exist.
    """

    def __init__(
        self,
        event_bus: ExternalEventBus,
        logger: RuntimeLoggingContext,
        config: RuntimeConfig,
    ) -> None:
        self._event_bus = event_bus
        self._logger = logger

        self._redis_url = config.md_redis_url

        self._tick_prefix = config.tick_pubsub_channel_prefix
        self._quote_prefix = config.quote_pubsub_channel_prefix
        self._partition_number = config.md_redis_partition_count

        self._targets: set[tuple[Symbol, Timeframe]] = set()
        self._symbols: set[Symbol] = set()

        self._tick_channels: set[str] = set()
        self._quote_channels: set[str] = set()

        self._redis: redis.Redis | None = None
        self._pubsub: PubSub | None = None

        self._is_running = False
        self._task: asyncio.Task[None] | None = None

        self._connection_lock = asyncio.Lock()
        self._lifecycle_lock = asyncio.Lock()

        # Used when the listener has no channels.
        # Waiting on this event is asynchronous and non-polling.
        self._channels_available = asyncio.Event()

        self._reconnect_initial_delay = 1.0
        self._reconnect_max_delay = 10.0

    # ------------------------------------------------------------------
    # Public state
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def targets(self) -> frozenset[tuple[Symbol, Timeframe]]:
        return frozenset(self._targets)

    @property
    def symbols(self) -> frozenset[Symbol]:
        return frozenset(self._symbols)

    # ------------------------------------------------------------------
    # Channel calculation
    # ------------------------------------------------------------------

    def _desired_channels(self) -> set[str]:
        return self._tick_channels | self._quote_channels

    def _calculate_channels(
        self,
        targets: set[tuple[Symbol, Timeframe]],
    ) -> tuple[set[str], set[str]]:
        tick_channels: set[str] = set()
        quote_channels: set[str] = set()

        # One symbol can have several timeframes, but the Redis channel
        # is determined only by the symbol's partition.
        symbols = {
            symbol
            for symbol, _ in targets
        }

        for symbol in symbols:
            partition = calculate_partition(
                symbol,
                self._partition_number,
            )

            tick_channels.add(
                f"{self._tick_prefix}{partition}",
            )

            quote_channels.add(
                f"{self._quote_prefix}{partition}",
            )

        return tick_channels, quote_channels

    # ------------------------------------------------------------------
    # Dynamic channel update
    # ------------------------------------------------------------------

    async def _apply_targets_locked(
        self,
        new_targets: set[tuple[Symbol, Timeframe]],
    ) -> None:
        """
        Apply targets while _connection_lock is already held.
        """
        new_symbols = {
            symbol
            for symbol, _ in new_targets
        }

        new_tick_channels, new_quote_channels = (
            self._calculate_channels(new_targets)
        )

        new_channels = new_tick_channels | new_quote_channels
        old_channels = self._desired_channels()

        channels_to_subscribe = new_channels - old_channels
        channels_to_unsubscribe = old_channels - new_channels

        # Save desired state before touching Redis.
        self._targets = new_targets
        self._symbols = new_symbols
        self._tick_channels = new_tick_channels
        self._quote_channels = new_quote_channels

        if new_channels:
            self._channels_available.set()
        else:
            self._channels_available.clear()

        if not self._is_running:
            return

        try:
            if self._pubsub is None:
                if new_channels:
                    await self._open_connection_locked()

                return

            # Subscribe first to minimize the transition gap.
            if channels_to_subscribe:
                await self._pubsub.subscribe(
                    *channels_to_subscribe,
                )

            if channels_to_unsubscribe:
                await self._pubsub.unsubscribe(
                    *channels_to_unsubscribe,
                )

            self._logger.platform_info(
                message="Market-data Redis channels updated",
                subscribed=channels_to_subscribe,
                unsubscribed=channels_to_unsubscribe,
            )

        except (RedisError, OSError) as exc:
            self._logger.platform_warning(
                message="Redis subscription update failed",
                subscribed=channels_to_subscribe,
                unsubscribed=channels_to_unsubscribe,
                exception=str(exc),
            )

            await self._close_connection_locked()
            
    async def add_channel(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        _
    ) -> None:
        target = (symbol, timeframe)

        async with self._connection_lock:
            if target in self._targets:
                return

            new_targets = set(self._targets)
            new_targets.add(target)

            await self._apply_targets_locked(new_targets)

            self._logger.platform_info(
                message="Add channel requested for indicator registration",
                symbol=symbol,
                timeframe=timeframe,
            )

    async def remove_channel(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        _: int | None = None
    ) -> None:
        target = (symbol, timeframe)

        async with self._connection_lock:
            if target not in self._targets:
                return

            new_targets = set(self._targets)
            new_targets.remove(target)

            await self._apply_targets_locked(new_targets)

    async def unsubscribe_all_channels(self) -> None:
        """
        Remove every market-data target and unsubscribe all Redis channels.

        The listener remains running. It waits asynchronously until a new
        target is added through add_channel() or set_channels().
        """
        async with self._connection_lock:
            if not self._targets and not self._desired_channels():
                return

            await self._apply_targets_locked(set())

    async def set_channels(
        self,
        ref: list[tuple[Symbol, Timeframe]],
    ) -> None:
        async with self._connection_lock:
            await self._apply_targets_locked(set(ref))

    async def update_targets(
        self,
        targets: list[tuple[Symbol, Timeframe]],
    ) -> None:
        await self.set_channels(targets)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _open_connection_locked(self) -> None:
        """
        Open Redis and subscribe to every currently desired channel.

        The caller must hold _connection_lock.
        """
        if self._redis is not None or self._pubsub is not None:
            return

        redis_client = redis.from_url(
            self._redis_url,
            decode_responses=True,
            socket_connect_timeout=5.0,
            health_check_interval=30,
        )

        pubsub: PubSub | None = None

        try:
            await redis_client.ping()

            pubsub = redis_client.pubsub(
                ignore_subscribe_messages=True,
            )

            channels = self._desired_channels()

            if channels:
                await pubsub.subscribe(*channels)

            self._redis = redis_client
            self._pubsub = pubsub

            self._logger.platform_info(
                message="Redis market-data connection opened"
            )

        except Exception:
            if pubsub is not None:
                await pubsub.aclose()

            await redis_client.aclose()
            raise

    async def _close_connection_locked(self) -> None:
        """
        Close the current Pub/Sub and Redis objects.

        The caller must hold _connection_lock.
        """
        pubsub = self._pubsub
        redis_client = self._redis

        self._pubsub = None
        self._redis = None

        if pubsub is not None:
            try:
                await pubsub.aclose()
            except Exception as exc:
                self._logger.platform_warning(
                    message="Failed to close Redis Pub/Sub",
                    exception=str(exc)
                )

        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception as exc:
                self._logger.platform_warning(
                    message="Failed to close Redis client",
                    exception=str(exc)
                )

    async def _recover_connection(
        self,
        failed_pubsub: PubSub | None,
    ) -> None:
        """
        Recreate the Redis connection after a connection failure.

        This retry delay is only used after a failure. It is not used
        for reading market-data messages.
        """
        delay = self._reconnect_initial_delay

        while self._is_running and self._desired_channels():
            async with self._connection_lock:
                # Another coroutine may already have replaced the connection.
                if (
                    self._pubsub is not None
                    and self._pubsub is not failed_pubsub
                ):
                    return

                if self._pubsub is failed_pubsub:
                    await self._close_connection_locked()

                try:
                    await self._open_connection_locked()

                    self._logger.platform_info(
                        "Redis market-data connection recovered",
                    )
                    return

                except asyncio.CancelledError:
                    raise

                except (RedisError, OSError) as exc:
                    self._logger.platform_warning(
                        message="Redis reconnect failed; Now retrying",
                        exception=str(exc)
                    )

                    await self._close_connection_locked()

            await asyncio.sleep(delay)

            delay = min(
                delay * 2.0,
                self._reconnect_max_delay,
            )

    async def restart_connection(self) -> None:
        """
        Explicitly recreate the Redis connection and consumer.

        Use this only for deliberate connection recovery, not for normal
        channel changes.
        """
        async with self._lifecycle_lock:
            if not self._is_running:
                return

            old_task = self._task
            self._task = None

            if old_task is not None:
                old_task.cancel()

                try:
                    await old_task
                except asyncio.CancelledError:
                    pass

            async with self._connection_lock:
                await self._close_connection_locked()

                if self._desired_channels():
                    await self._open_connection_locked()

            self._task = asyncio.create_task(
                self._consume(),
                name="redis-market-data-listener",
            )

    async def restart(self) -> None:
        await self.restart_connection()

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_payload(
        raw_data: Any,
    ) -> dict[str, Any] | None:
        if isinstance(raw_data, dict):
            return raw_data

        if isinstance(raw_data, bytes):
            try:
                raw_data = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                return None

        if not isinstance(raw_data, str):
            return None

        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    async def _publish_event(
        self,
        event_type: str,
        symbol: str,
        payload: dict[str, Any],
    ) -> None:
        result = self._event_bus.publish(
            {
                "type": event_type,
                "symbol": symbol,
                "payload": payload,
            }
        )        

        # Supports either a synchronous or asynchronous event bus.
        if inspect.isawaitable(result):
            await result

    async def _handle_message(
        self,
        message: dict[str, Any],
    ) -> None:
        if message.get("type") != "message":
            return

        channel = message.get("channel")
        if isinstance(channel, bytes):
            try:
                channel = channel.decode("utf-8")
            except UnicodeDecodeError:
                return

        if not isinstance(channel, str):
            return
        payload = self._decode_payload(
            message.get("data"),
        )

        if payload is None:
            self._logger.platform_warning(
                "Ignoring invalid market-data message on channel %s",
                channel,
            )
            return
        
        symbol = payload.get("symbol")

        if not isinstance(symbol, str):
            return

        # Several symbols can share the same partition channel.
        if symbol not in self._symbols:
            return
        
        print(f"------{channel}")
        print(payload)

        if channel.startswith(self._quote_prefix):
            new_quote = from_raw_to_quote(payload)
            await self._publish_event(
                event_type=ExternalEventType.QUOTE,
                symbol=symbol,
                payload= new_quote
            )

        elif channel.startswith(self._tick_prefix):
            new_tick = from_raw_to_tick(payload)
            await self._publish_event(
                event_type=ExternalEventType.TICK,
                symbol=symbol,
                payload=new_tick
            )

    # ------------------------------------------------------------------
    # Main event-driven consumer
    # ------------------------------------------------------------------

    async def _consume(self) -> None:
        """
        Wait for channels, then listen for Redis messages.

        No message polling and no timeout loop are used here.
        """
        try:
            while self._is_running:
                # When there are no targets, wait asynchronously until
                # set_channels() adds at least one channel.
                await self._channels_available.wait()

                if not self._is_running:
                    break

                pubsub = self._pubsub

                if pubsub is None:
                    await self._recover_connection(
                        failed_pubsub=None,
                    )
                    continue

                try:
                    # Event-driven Redis socket listener.
                    async for message in pubsub.listen():
                        if not self._is_running:
                            return

                        try:
                            await self._handle_message(message)

                        except asyncio.CancelledError:
                            raise

                        except Exception as exc:
                            # A malformed payload or event-bus failure must
                            # not permanently terminate Redis consumption.
                            self._logger.platform_warning(
                                "Failed to process market-data message",
                                exception=str(exc)
                            )

                    # listen() ends when every channel has been unsubscribed.
                    # The outer loop then waits on _channels_available.
                    continue

                except asyncio.CancelledError:
                    raise

                except (RedisError, OSError) as exc:
                    self._logger.platform_warning(
                        message="Redis market-data connection failed: %s",
                        exception=str(exc)
                    )

                    await self._recover_connection(
                        failed_pubsub=pubsub,
                    )

        except asyncio.CancelledError:
            raise

        finally:
            self._logger.platform_info(
                message="Redis market-data consumer stopped"
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        async with self._lifecycle_lock:
            if self._is_running:
                return

            self._is_running = True

            if self._desired_channels():
                self._channels_available.set()
            else:
                self._channels_available.clear()

            try:
                async with self._connection_lock:
                    if self._desired_channels():
                        await self._open_connection_locked()

                self._task = asyncio.create_task(
                    self._consume(),
                    name="redis-market-data-listener",
                )

            except Exception:
                self._is_running = False

                async with self._connection_lock:
                    await self._close_connection_locked()

                raise

    async def stop(self) -> None:
        async with self._lifecycle_lock:
            if not self._is_running and self._task is None:
                return

            self._logger.platform_info(
                message="Stopping Redis market-data listener",
            )

            self._is_running = False

            # Wake _consume() if it is waiting for channels.
            self._channels_available.set()

            task = self._task
            self._task = None

            if task is not None:
                self._logger.platform_info(
                    message="Cancelling Redis market-data consumer",
                )

                task.cancel()

                try:
                    await asyncio.wait_for(
                        task,
                        timeout=5.0,
                    )
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    self._logger.platform_warning(
                        message="Redis consumer did not stop within timeout",
                    )
                except Exception as exc:
                    self._logger.platform_warning(
                        message="Redis consumer failed during shutdown",
                        exception=str(exc),
                    )

            self._logger.platform_info(
                message="Closing Redis market-data connection",
            )

            try:
                await asyncio.wait_for(
                    self._close_connection_safely(),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                self._logger.platform_warning(
                    message="Redis connection close timed out",
                )

            self._channels_available.clear()

            self._logger.platform_info(
                message="Redis market-data listener stopped",
            )


    async def _close_connection_safely(self) -> None:
        async with self._connection_lock:
            await self._close_connection_locked()
