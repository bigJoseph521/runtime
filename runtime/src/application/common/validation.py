def validate_symbol(symbol: str) -> None:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("Invalid symbol")


def resolve_limit(
    limit: int | None = None,
    *,
    default: int = 500,
    max_limit: int = 5000,
) -> int:
    if limit is None:
        return default
    if limit <= 0:
        raise ValueError("limit must be > 0")
    return min(limit, max_limit)