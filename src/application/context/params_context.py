from __future__ import annotations

import sys

from pathlib import Path
from typing import Any
import yaml

import asyncio

from alphovex_sdk.context.params_context import ParamsContext
from alphovex_sdk.errors.validation import InvalidValueError

from application.context.logging_context import RuntimeLoggingContext
from application.status_managing.manager import StatusManager
from application.status_managing.status_model import Status

class RuntimeParamsContext(ParamsContext):
    def __init__(
        self, 
        yaml_path: str, 
        logger: RuntimeLoggingContext,
        status_manager: StatusManager
    ):
        self._yaml_path = yaml_path
        self._logger = logger
        self._params : dict[str, Any] = self._set_params_from_yaml()
        self._status_manager = status_manager

    def _set_params_from_yaml(self) -> dict[str, Any] | None :
        if not Path(self._yaml_path).exists():
            self._logger.error(
                message="'params.yaml' file no exist"
            )
            self._status_manager.transform(new_status= Status.FAILED)
            
        with open(self._yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            self._logger.error(
                message="Invalid yaml file, it must be dict foramt",
                file = "params.yaml"
            )
            self._status_manager.transform(new_status=Status.FAILED)
            raise InvalidValueError(
                message="Yaml must be a dictionary",
                details={"file": "params.yaml"}
            )
        data = data.get("params")
        return data
    
    def set_params(self, paramDict: dict[str, Any]):
        if self._params.keys() <= paramDict.keys():
            self._params.update(paramDict)
            self._logger.platform_info(
                message="Params updated based on deployment info"
            )
        else:
            self._logger.error(
                message="Invalid param detected",
                invalid_params=list(paramDict.keys() - self._params.keys())
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
    
    def get_params(self, *keys) -> tuple[Any, ...]:
        missing = [k for k in keys if k not in self._params]
        if missing:
            self._logger.error(
                message="Not defined Params",
                invalid_params=missing
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
            raise KeyError(f"Missing parameters: {missing}")

        return tuple(self._params[k] for k in keys)
    
    def get(self, key) -> Any:
        return self._params.get(key)
        
    