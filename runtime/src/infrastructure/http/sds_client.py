from __future__ import annotations

import httpx
from pydantic import ValidationError

from infrastructure.http.dtos import DeploymentInfoDTO, StateUpdateDTO
from application.context.logging_context import RuntimeLoggingContext
from application.status_managing.status_model import Status
from application.event_handling.internal_event_bus import InternalEventBus
from application.event_handling.events_model import InternalEventType

class SDSHTTPClient:
    def __init__(
        self, 
        sds_base_url: str,
        deployment_id: str,
        http_timeout: int,
        logger: RuntimeLoggingContext,
        event_bus: InternalEventBus
    ):
        """
        set_status_handler is StateManager.transform() function 
        """
        self._sds_base_url = sds_base_url
        self._timeout = http_timeout
        self._deployment_id = deployment_id
        self._client = httpx.AsyncClient(timeout=self._timeout, trust_env=False)
        self._logger = logger
        self._event_bus = event_bus
    
    async def close(self):
        await self._client.aclose()

    async def get_deployment_info(self) -> DeploymentInfoDTO | None:
        url = f"{self._sds_base_url}/deploy_metadata"
        params = {
            "id": self._deployment_id
        }
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            deployment_info = DeploymentInfoDTO.model_validate(data)
            self._logger.platform_info(
                message="Deployment info fetched successfully",
                response= response.text
            )

            return deployment_info

        except httpx.HTTPError as e:
            self._logger.platform_error(
                message="HTTP request failed when fetching deployment info",
                error=str(e),
                url=url,
            )
            await self._event_bus.publish({
                "type": InternalEventType.STATUS_CHANGED,
                "new_status": Status.FAILED
            })
            return None

        except ValidationError as e:
            invalid_fields = [
                ".".join(map(str, err.get("loc", [])))
                for err in e.errors()
            ]

            self._logger.platform_error(
                message="Deployment info from SDS is invalid",
                invalid_fields=invalid_fields,
                raw_response=response.text if "response" in locals() else None,
            )
            await self._event_bus.publish({
                "type": InternalEventType.STATUS_CHANGED,
                "new_status": Status.FAILED
            })
            return None
    
    async def report_status_update(self, new_status: Status):
        url = f"{self._sds_base_url}/status"
        request_body = StateUpdateDTO(
            deployment_id= self._deployment_id,
            runtime_state= new_status
        )

        try:
            response = await self._client.post(
                url= url,
                data= request_body.model_dump(),
            )
            response.raise_for_status()
            self._logger.platform_info(
                message="Status Updates reported",
                status=str(new_status)
            )
        except httpx.HTTPError as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            response_text = getattr(getattr(e, "response", None), "text", None)
            self._logger.platform_warning(
                message="Status Update Report Failed",
                status=status_code,
                error=str(e),
                response=response_text
            )        
            
