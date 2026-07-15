from __future__ import annotations

from typing import Any

from importlib import import_module
import asyncio
from pathlib import Path
from urllib.parse import urlparse, unquote
from urllib.request import url2pathname
import shutil
import time

from application.ports.strategy_loader import StrategyLoaderPort
from application.context.logging_context import RuntimeLoggingContext
from application.status_managing.manager import StatusManager
from application.status_managing.status_model import Status
from infrastructure.config.config import RuntimeConfig


from application.strategy_validation.strategy_validate import sha256_check, check_folder_with_mypy

class LocalStrategyLoader(StrategyLoaderPort):
    def __init__(
            self, 
            logger: RuntimeLoggingContext, 
            config: RuntimeConfig,
            status_manager: StatusManager
        ):
        self._strategy_local_path = config.strategy_local_path
        self._strategy_uri = config.strategy_uri
        self._strategy_digest = config.strategy_zipfile_sha256
        self._strategy_entrypoint = config.strategy_entrypoint
        self._status_manager= status_manager
        self._logger = logger

    def _resolve_file_path(self, value: str) -> Path:
        parsed = urlparse(value)

        if parsed.scheme == "file":
            return Path(url2pathname(unquote(parsed.path)))

        return Path(value)
    
    def load_strategy(self) -> type[Any]:
        file_path = self._resolve_file_path(self._strategy_uri)
        if file_path.exists():
            is_valid = sha256_check(file_path=file_path, value=self._strategy_digest)
            if is_valid:
                shutil.unpack_archive(file_path, self._strategy_local_path)
                self._sdk_compatibility_check()
                strategy_class = self._get_class()
                self._logger.platform_info(
                    message="Strategy File succuessfully installed"
                )
                return strategy_class
            else:
                self._logger.platform_error(
                    message="Strategy File is broken"
                )
                asyncio.create_task(
                    self._status_manager.transform(new_status=Status.FAILED)
                )

                time.sleep(1.0)
                raise ValueError("Strategy File is broken, sha256 values mismatch")
        else:
            self._logger.platform_error(
                message="Strategy File not exist on the path given by SDS",
                path=str(file_path)
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
            time.sleep(1.0)
            raise ValueError("Strategy File not exist on the path given by SDS")
            
    
    def _sdk_compatibility_check(self):
        check_results = check_folder_with_mypy(folder_path= self._strategy_local_path)
        if len(check_results):
            for result in check_results:
                self._logger.error(
                    message = "Invalid Strategy code",
                    error_message = result["message"],
                    error_type = result["type"],
                    file = result["file"],
                    row = result["row"],
                    column = result["column"]
                )
                self._logger.platform_error(
                    message = "Invalid Strategy code",
                    source = "User",
                    error_message = result["message"],
                    error_type = result["type"],
                    file = result["file"],
                    row = result["row"],
                    column = result["column"]
                )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
            
            time.sleep(1.0)
            raise ValueError("SDK Compatibility check failed: Invalid Strategy Code")



    def _get_class(self) -> type[Any]:
        module_name, seperator, class_name = self._strategy_entrypoint.partition(":")

        module_name = module_name.strip()
        class_name = class_name.strip()

        if not seperator or not module_name or not class_name:
            self._logger.error(
                message="Strategy must use the format 'module_name:ClassName'",
                value=self._strategy_entrypoint
            )
            self._logger.platform_error(
                message="Caused by user, Strategy must use the format 'module_name:ClassName'",
                value=self._strategy_entrypoint,
                source="User"
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
            time.sleep(1.0)
            raise ValueError(
                "Strategy must use the format 'module_name:ClassName'"
            )

        full_module_path = f"strategy.{module_name}"

        try:
            module = import_module(full_module_path)
        except ModuleNotFoundError as exc:
            self._logger.error(
                message="Module not found"
            )
            self._logger.platform_error(
                message="Module not found",
                exception=str(exc)
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
            time.sleep(1.0)
            raise ImportError(
                f"Could not import strategy module '{full_module_path}'"
            ) from exc

        try:
            strategy_class = getattr(module, class_name)
            
        except AttributeError as exc:
            self._logger.error(
                message="Class not found"
            )
            self._logger.platform_error(
                message="Class not found",
                exception=str(exc)
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )
            time.sleep(1.0)
            raise ImportError(
                f"Module '{full_module_path}' does not contain class '{class_name}'"
            ) from exc

        if not isinstance(strategy_class, type):
            self._logger.error(
                message="Entrypoint must indicate class, not function or variable"
            )
            self._logger.platform_error(
                message="Entrypoint must indicate class, not function or variable",
                exception=str(exc)
            )
            time.sleep(1.0)
            raise TypeError(
                f"'{class_name}' in '{full_module_path}' is not a class"
            )

        return strategy_class

    




    

