from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Collection
from typing import Any

import redis.asyncio as redis
from redis.asyncio.client import PubSub
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    RedisError,
)

from application.context.logging_context import RuntimeLoggingContext

from application.event_handling.external_event_bus import (
    ExternalEventBus,
    ExternalEventType
)

class RedisTradingStateListener:
    """
    Redis Pub/Sub listener for trading-state updates.

    Characteristics:
    - Channels are fixed during initialization.
    - Uses PubSub.listen(); it does not poll Redis.
    - Runs in one background asyncio task.
    - Reconnects indefinitely when the connection fails.
    - Re-subscribes to all fixed channels after reconnecting.
    """

    def __init__(
        self,
        event_bus: ExternalEventBus,
        redis_url: str,
        channels: Collection[str],
        logger: RuntimeLoggingContext,
        *,
        reconnect_initial_delay: float = 1.0,
        reconnect_max_delay: float = 10.0,
    ) -> None:
        if isinstance(channels, str):
            raise TypeError(
                "channels must be a collection of channel names, "
                "not a single string",
            )

        normalized_channels: set[str] = set()

        for channel in channels:
            if not isinstance(channel, str):
                raise TypeError(
                    "Every Redis channel must be a string",
                )

            normalized_channel = channel.strip()

            if not normalized_channel:
                raise ValueError(
                    "Redis channel names cannot be empty",
                )

            normalized_channels.add(normalized_channel)

        if not normalized_channels:
            raise ValueError(
                "RedisTradingStateListener requires at least one channel",
            )

        if reconnect_initial_delay <= 0:
            raise ValueError(
                "reconnect_initial_delay must be greater than zero",
            )

        if reconnect_max_delay < reconnect_initial_delay:
            raise ValueError(
                "reconnect_max_delay cannot be less than "
                "reconnect_initial_delay",
            )

        self._event_bus = event_bus
        self._logger = logger
        self._redis_url = redis_url
        self._channels = frozenset(normalized_channels)

        self._reconnect_initial_delay = reconnect_initial_delay
        self._reconnect_max_delay = reconnect_max_delay

        self._redis: redis.Redis | None = None
        self._pubsub: PubSub | None = None

        self._is_running = False
        self._task: asyncio.Task[None] | None = None

        self._connected = asyncio.Event()
        self._lifecycle_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public state
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def channels(self) -> frozenset[str]:
        return self._channels

    # ------------------------------------------------------------------
    # Redis connection
    # ------------------------------------------------------------------

    async def _open_connection(self) -> None:
        """
        Create a new Redis client and Pub/Sub object.

        Every successful call creates a fresh connection and subscribes
        to every fixed channel.
        """
        if self._redis is not None or self._pubsub is not None:
            raise RuntimeError(
                "Redis trading-state connection is already open",
            )

        redis_client = redis.from_url(
            self._redis_url,
            decode_responses=True,
            socket_connect_timeout=5.0,
            socket_keepalive=True,
            health_check_interval=30,
        )

        pubsub: PubSub | None = None

        try:
            # This verifies that Redis can currently be reached.
            await redis_client.ping()

            pubsub = redis_client.pubsub(
                ignore_subscribe_messages=True,
            )

            # Subscribing opens the dedicated Pub/Sub connection.
            await pubsub.subscribe(
                *self._channels,
            )

            self._redis = redis_client
            self._pubsub = pubsub
            self._connected.set()

            self._logger.platform_infoinfo(
                message="Redis trading-state listener connected; channels=%s",
                channels = sorted(self._channels),
            )

        except BaseException:
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception as exc:
                    self._logger.platform_warning(
                        message="Failed to close unsuccessful Redis Pub/Sub",
                        exception=str(exc)
                    )

            try:
                await redis_client.aclose()
            except Exception as exc:
                self._logger.platform_warning(
                    message="Failed to close unsuccessful Redis client",
                    exception=str(exc)
                )

            raise

    async def _close_connection(self) -> None:
        """
        Close the current Redis Pub/Sub object and Redis client.

        This method is safe to call multiple times.
        """
        pubsub = self._pubsub
        redis_client = self._redis

        # Remove references before awaiting cleanup.
        self._pubsub = None
        self._redis = None
        self._connected.clear()

        if pubsub is not None:
            try:
                await pubsub.aclose()
            except Exception as exc:
                self._logger.platform_warning(
                    message="Failed to close Redis trading-state Pub/Sub",
                    exception=str(exc)
                )

        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception as exc:
                self._logger.platform_warning(
                    message="Failed to close Redis trading-state client",
                    exception= str(exc)
                )

    # ------------------------------------------------------------------
    # Message decoding
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_channel(
        raw_channel: Any,
    ) -> str | None:
        if isinstance(raw_channel, str):
            return raw_channel

        if isinstance(raw_channel, bytes):
            try:
                return raw_channel.decode("utf-8")
            except UnicodeDecodeError:
                return None

        return None

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

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    async def _publish_event(
        self,
        event: dict[str, Any],
    ) -> None:
        """
        Support either a synchronous or asynchronous event bus.
        """
        result = self._event_bus.publish(event)

        if inspect.isawaitable(result):
            await result

    async def _handle_message(
        self,
        message: dict[str, Any],
    ) -> None:
        if message.get("type") != "message":
            return

        channel = self._decode_channel(
            message.get("channel"),
        )

        if channel is None:
            self._logger.platform_warning(
                message="Ignoring trading-state message with invalid channel",
            )
            return

        # The listener only accepts its initialized channel set.
        if channel not in self._channels:
            return

        payload = self._decode_payload(
            message.get("data"),
        )

        if payload is None:
            self._logger.platform_warning(
                message="Ignoring invalid trading-state payload",
                channel = channel,
            )
            return

        await self._publish_event(
            {
                "type": ExternalEventType.ORDER_UPDATE,
                "channel": channel,
                "payload": payload,
            }
        )

    async def _publish_reconnected_event(self) -> None:
        """
        Tell the runtime that Redis was disconnected and later restored.

        The runtime can use this event to reload current state from its
        authoritative services.
        """
        await self._publish_event(
            {
                "type": "trading_state_resync_required",
                "payload": {
                    "channels": sorted(self._channels),
                },
            }
        )

    # ------------------------------------------------------------------
    # Main listener and reconnection loop
    # ------------------------------------------------------------------

    async def _consume(self) -> None:
        """
        Connect and listen continuously.

        A successful Redis connection can process any number of messages.
        Reconnection starts only when:

        - opening the connection fails;
        - PubSub.listen() raises a Redis/network error; or
        - PubSub.listen() ends unexpectedly.
        """
        reconnect_delay = self._reconnect_initial_delay
        has_connected_before = False

        try:
            while self._is_running:
                try:
                    await self._open_connection()

                    if has_connected_before:
                        self._logger.platform_info(
                            "Redis trading-state connection restored",
                        )

                        await self._publish_reconnected_event()

                    has_connected_before = True

                    # Reset backoff after every successful connection.
                    reconnect_delay = self._reconnect_initial_delay

                    pubsub = self._pubsub

                    if pubsub is None:
                        raise RuntimeError(
                            "Redis Pub/Sub was not created",
                        )

                    # One connection processes any number of messages.
                    # Receiving a message does not cause reconnection.
                    async for message in pubsub.listen():
                        if not self._is_running:
                            return

                        try:
                            await self._handle_message(message)

                        except asyncio.CancelledError:
                            raise

                        except Exception as exc:
                            # A malformed message or event-handler error
                            # should not restart the Redis connection.
                            self._logger.platform_warning(
                                message="Failed to process trading-state message",
                                exception=str(exc)
                            )

                    # Fixed channels are never intentionally unsubscribed.
                    # Therefore, listen() ending while running is treated
                    # as a failed connection.
                    if self._is_running:
                        raise RedisConnectionError(
                            "Redis Pub/Sub listen loop ended unexpectedly",
                        )

                except asyncio.CancelledError:
                    raise

                except (
                    RedisError,
                    OSError,
                    EOFError,
                ) as exc:
                    self._logger.platform_warning(
                        message="Redis trading-state connection failed: %s",
                        exception = str(exc),
                    )

                finally:
                    # This runs after the entire listen loop ends or fails,
                    # not after each individual message.
                    await self._close_connection()

                if not self._is_running:
                    break

                self._logger.info(
                    message=f"Reconnecting Redis trading-state listener in {reconnect_delay} seconds",
                )

                # This sleep is only reconnection backoff.
                # It is not Redis message polling.
                await asyncio.sleep(reconnect_delay)

                reconnect_delay = min(
                    reconnect_delay * 2.0,
                    self._reconnect_max_delay,
                )

        except asyncio.CancelledError:
            raise

        finally:
            await self._close_connection()

            self._logger.platform_info(
                "Redis trading-state listener stopped",
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Start the listener background task.

        This method returns immediately after creating the task. If Redis
        is unavailable, the task keeps trying to connect.
        """
        async with self._lifecycle_lock:
            if self._is_running:
                return

            self._is_running = True

            self._task = asyncio.create_task(
                self._consume(),
                name="redis-trading-state-listener",
            )

    async def stop(self) -> None:
        """
        Stop listening, stop reconnection attempts, and close Redis.
        """
        async with self._lifecycle_lock:
            if not self._is_running and self._task is None:
                return

            self._is_running = False

            task = self._task
            self._task = None

            if task is not None:
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass

            await self._close_connection()