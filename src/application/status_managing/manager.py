from __future__ import annotations

import sys
from enum import StrEnum

from application.context.logging_context import RuntimeLoggingContext
from application.status_managing.status_model import Status
from infrastructure.http.sds_client import SDSHTTPClient

class StatusManager:
    def __init__(
            self, 
            logger: RuntimeLoggingContext, 
            report_client: SDSHTTPClient
        ):
        self._status : Status = Status.INITIALIZING
        self._valid_transforms = self._make_valid_transform_status_pairs()
        self._logger = logger
        self._report_client = report_client
        
    async def transform(self, new_status: Status):
        if self.is_valid(new_status=new_status):
            self._logger.platform_info(
                message="Status updated",
                old_status=str(self._status),
                new_status=str(new_status)
            )

            self._status = new_status

            await self._report_client.report_status_update(new_status=new_status)

            if new_status == Status.FAILED:
                sys.exit(0)

        else:
            self._logger.platform_error(
                message="Invalid status transformation",
                old_status=str(self._status),
                new_status=str(new_status)
            )

    def is_valid(self, new_status: Status) -> bool:
        return new_status in self._valid_transforms.get(self._status, set())

    def _make_valid_transform_status_pairs(self) -> dict[Status, set[Status]]:
        pairs :dict[Status, set[Status]] = {}
        
        status_from_initializing = {Status.STARTING, Status.FAILED, Status.STOPPING}
        pairs[Status.INITIALIZING] = status_from_initializing
        
        status_from_starting = {Status.RUNNING, Status.FAILED, Status.STOPPING}
        pairs[Status.STARTING] = status_from_starting

        status_from_running = {Status.STOPPING, Status.DEGRADED, Status.FAILED, Status.COMPLETED}
        pairs[Status.RUNNING] = status_from_running

        status_from_stopping = {Status.STOPPED, Status.FAILED}
        pairs[Status.STOPPING] = status_from_stopping

        return pairs

    def get_status(self) -> Status:
        return self._status


