from __future__ import annotations

import httpx

from alphovex_sdk.typedefs.aliases import Timeframe
from application.context.logging_context import RuntimeLoggingContext
from application.ports.historical_data import HistoricalDataClientPort
from contracts.rows import _BarRow
from infrastructure.redis.helpers import to_numpy_datetime64_utc

class HistoricalDataServiceClient(HistoricalDataClientPort):
    def __init__(
        self,
        hds_base_url: str,
        time_out: int,
        logger: RuntimeLoggingContext,
    ):
        self._hds_base_url = hds_base_url
        self._client = httpx.AsyncClient(timeout=time_out, trust_env=False)
        self._logger = logger

    async def get_bar_history(
        self,
        symbol: str,
        timeframe: Timeframe,
        window: int
    ) -> list[_BarRow]:
        url = f"{self._hds_base_url}/history"
        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "window": window
        }
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Expected the API reponse to be a list")

            _BarRows = []
            for item in data:
                new_bar = self._from_raw_to_bar(item)
                _BarRows.append(new_bar)
            return _BarRows

        except httpx.HTTPError as e:
            self._logger.platform_error(
                message="HTTP Request failed when fetching historical bar data",
                error=str(e),
                url=url
            )

            return []
    
    def _from_raw_to_bar(
        self,
        raw,
    ) -> _BarRow:
        new_Bar = _BarRow(
            ts= to_numpy_datetime64_utc(raw["time_utc"]),
            open=raw["open"],
            high=raw["high"],
            low=raw["low"],
            close=raw["close"],
            volume=raw["volume"]
        )
        return new_Bar
        
        