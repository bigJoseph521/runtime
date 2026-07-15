# Runtime wiring fixes

- Passed the already-created `position_context` into `RuntimeOrderContext`.
- Made `RuntimePositionContext` retain the deployment position snapshot.
- Constructed `_active_orders` as a real deque rather than a generic alias.
- Corrected active-order ID lookup, terminal-state property access, update
  timestamp spelling, and recent-order deque slicing.

## Historical data gRPC migration

- Replaced the REST historical-data adapter with
  `GRPCHistoricalDataClient`.
- Uses `historical_data.HistoricalDataService/QueryHistoricalData` with the
  current protobuf contract.
- Requests newest-first pages and converts them to oldest-first warm-up rows
  before replay.
- Handles the service's stored-range boundary metadata with one bounded retry.
- Keeps historical I/O in asynchronous `WarmUpService`; synchronous SDK data
  reads now access only the in-memory ring buffer.
- Closes the historical gRPC channel during runtime shutdown.

Required environment:

```dotenv
HISTORICAL_DATA_GRPC_TARGET=127.0.0.1:52051
HISTORICAL_DATA_GRPC_TIMEOUT_SECONDS=10
```
