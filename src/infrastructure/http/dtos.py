from __future__ import annotations

from typing import Any, get_type_hints
from dataclasses import MISSING, fields, is_dataclass
from pydantic import BaseModel, Field, create_model, ConfigDict

from alphovex_sdk import (
    Account,
    Position,
    Order
)

from domain.model import RuntimeMode
from application.status_managing.status_model import Status

def dataclass_to_model(
    dataclass_type: type[Any],
) -> type[BaseModel]:
    if not is_dataclass(dataclass_type):
        raise TypeError(
            f"{dataclass_type!r} is not a dataclass"
        )

    type_hints = get_type_hints(dataclass_type)
    model_fields: dict[str, tuple[Any, Any]] = {}

    for dataclass_field in fields(dataclass_type):
        field_type = type_hints[dataclass_field.name]

        if dataclass_field.default is not MISSING:
            default = dataclass_field.default

        elif dataclass_field.default_factory is not MISSING:
            default = Field(
                default_factory=dataclass_field.default_factory
            )

        else:
            default = ...

        model_fields[dataclass_field.name] = (
            field_type,
            default,
        )

    return create_model(
        f"{dataclass_type.__name__}Model",
        **model_fields,
    )

class DeploymentInfoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: RuntimeMode
    deployment_id: str
    entrypoint: str
    artifact_uri: str
    params: dict[str, Any]
    artifact_digest: str

    account: Account
    positions: list[Position]
    # orders: list[Order]


class StateUpdateDTO(BaseModel):
    deployment_id: str
    runtime_state: Status