# Runtime wiring fixes

- Passed the already-created `position_context` into `RuntimeOrderContext`.
- Made `RuntimePositionContext` retain the deployment position snapshot.
- Constructed `_active_orders` as a real deque rather than a generic alias.
- Corrected active-order ID lookup, terminal-state property access, update
  timestamp spelling, and recent-order deque slicing.
