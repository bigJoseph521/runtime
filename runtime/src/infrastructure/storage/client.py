from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
from typing import Any
import json

from application.utils import to_jsonl_text

class StorageClient:
    def __init__(
            self, 
            storage_path: str,
            market_data_path: str,
        ):
        self._storage_path = storage_path
        self._market_data_path = market_data_path
        self._fundamental_parquet_path = f"{market_data_path}/fundamental.parquet"
    
    def store_order(self, record: str):
        with open(self._storage_path + "/orders.jsonl", "a", encoding="utf-8") as f:
            f.write(record + "\n")
    
    def store_user_log(self, record: str):
        with open(self._storage_path + "/user_logs.jsonl", "a", encoding="utf-8") as f:
            f.write(record + "\n")
    
    def store_platform_log(self, record: str):
        with open(self._storage_path + "/platform_logs.jsonl", "a", encoding="utf-8") as f:
            f.write(record + "\n")

    def get_daily_stock_summary(self, date: str) -> Any: 
        path = Path(f"{self._market_data_path}/daily_stock_summary/{date}.parquet")

        try:
            df = pd.read_parquet(
                path,
                columns=["symbol", "open", "high", "low", "close", "volume"]
            )
        except FileNotFoundError:
            self.store_platform_log(to_jsonl_text(
                log_level="error",
                message= "Daily stock summary no exist",
                date=date
            ))
            return None

        if df.empty:
            self.store_platform_log(to_jsonl_text(
                log_level="warning",
                message= "Empty Daily stock summary",
                date=date
            ))
            return None

        return df
    
    def get_fundamentals(
        self
    ) -> Any:       
        path = Path(f"{self._market_data_path}/fundamental.parquet")

        try:
            df = pd.read_parquet(path)
        except FileNotFoundError:
            self.store_platform_log(to_jsonl_text(
                log_level="error",
                message= "Fundamental data no exist"
            ))
            return None

        if df.empty:
            self.store_platform_log(to_jsonl_text(
                log_level="warning",
                message= "Empty Fundamental Data",
            ))
            return None

        return df
    
        

    # def load_batch_calculation_data(
    #     self,
    #     date_list: list[str],
    #     symbols: list[str] | str = "ALL"
    # ) -> BatchCalculationData | None:

    #     ohlcv_by_time = []

    #     # define symbol universe ONCE
    #     if symbols == "ALL":
    #         symbol_list = None
    #     else:
    #         symbol_list = list(symbols)

    #     for date in date_list:
    #         path = Path(f"{self._market_data_path}/daily_stock_summary/{date}.parquet")

    #         try:
    #             df = pd.read_parquet(
    #                 path,
    #                 columns=["symbol", "open", "high", "low", "close", "volume"]
    #             )
    #         except FileNotFoundError:
    #             self.store_platform_log(to_jsonl_text(
    #                 log_level="error",
    #                 message= "Daily stock summary no exist",
    #                 date=date
    #             ))
    #             return None

    #         if df.empty:
    #             return None

    #         # filter if needed
    #         if symbol_list is not None:
    #             self.store_platform_log(to_jsonl_text(
    #                 log_level="warning",
    #                 message= "Empty Daily stock summary",
    #                 date=date
    #             ))
    #             df = df[df["symbol"].isin(symbol_list)]

    #         # if ALL → define universe from first file only ONCE
    #         if symbol_list is None and len(ohlcv_by_time) == 0:
    #             symbol_list = df["symbol"].tolist()

    #         df = df.set_index("symbol").reindex(symbol_list)

    #         ohlcv_by_time.append(
    #             df[["open", "high", "low", "close", "volume"]].to_numpy()
    #         )

    #     data = np.stack(ohlcv_by_time, axis=0)

    #     return BatchCalculationData(
    #         open=data[:, :, 0],
    #         high=data[:, :, 1],
    #         low=data[:, :, 2],
    #         close=data[:, :, 3],
    #         volume=data[:, :, 4],
    #         symbols=tuple(symbol_list)
    #     )

    def store_user_record(self, key: str, value: Any):
        file_path = os.path.join(self._storage_path, "user_record.json")

        # Load existing data (or start fresh)
        data = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
            except (json.JSONDecodeError, FileNotFoundError):
                data = {}

        # Update or add key
        data[key] = value

        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user_record(self, key: str, default: Any) -> Any:
        file_path = os.path.join(self._storage_path, "user_record.json")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                data = json.loads(content) if content else {}
        except (FileNotFoundError, json.JSONDecodeError):
            self.store_platform_log(to_jsonl_text(
                log_level="error",
                message= "User Record no exist"
            ))
            return None

        return data.get(key, default=default)
