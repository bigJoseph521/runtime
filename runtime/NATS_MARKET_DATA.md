# NATS market-data integration

The runtime now uses `NATSMarketDataClient` instead of `RedisMarketDataListener`.

## Configuration

```env
NATS_SERVER_URL=nats://127.0.0.1:4222
NATS_SUBJECT_PREFIX=md
TIMEFRAME_SERVICE_BASE_URL=http://127.0.0.1:50120
HTTP_TIMEOUT=10
```

Install the required clients:

```bash
pip install nats-py httpx
```

## Subject ownership

For every active symbol the runtime shares these subscriptions across all registered timeframes:

```text
md.{SYMBOL}.bar
md.{SYMBOL}.quote
```

For each active custom timeframe it additionally subscribes to:

```text
md.{SYMBOL}.bar.{TIMEFRAME}
```

Example for `AAPL` with `1m`, `5m`, and `15m`:

```text
md.AAPL.bar
md.AAPL.quote
md.AAPL.bar.5m
md.AAPL.bar.15m
```

Removing `5m` only removes `md.AAPL.bar.5m`. The shared 1m and quote subjects remain until the last AAPL target is removed.

Custom timeframes acquire a REST lease from timeframe-service, renew it every 30 seconds, and release it during unregistration or shutdown.

## Lifecycle methods

```python
await client.start()
await client.add_channel("AAPL", "5m")
await client.remove_channel("AAPL", "5m")
await client.unsubscribe_all_channels()
await client.stop()
```
