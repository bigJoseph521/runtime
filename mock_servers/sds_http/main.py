# mock_sds_server.py

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel


app = FastAPI(title="Mock SDS Server")


DEPLOYMENT_ID = "25831484-fe6c-4af5-ae9b-7f35a8067363"

deployments: dict[str, dict[str, Any]] = {
    DEPLOYMENT_ID: {
        "mode": "paper",
        "deployment_id": DEPLOYMENT_ID,
        "entrypoint": "sma_crossover:SMACrossOver",
        "artifact_uri": "./data/samples/strategy-1/mystrategy.zip",
        "params": {
            "fast": 10,
            "slow": 30,
        },
        "account": {
            "cash_balance": 12000,
            "buying_power": 12000,
            "equity": 12000,
            "initial_margin": 0,
            "maintenance_margin": 0,
            "available_funds": 12000,
            "broker": "Alpaca"
        },
        "positions": [],
        # "orders": [],
        "artifact_digest": "b7b2a976dffef351bc2b8b422fd288ac8136090fc7a32faf523ca857d0c163e9",
    }
}

deployment_statuses: dict[str, str] = {}


@app.get("/deploy_metadata")
async def get_deployment_metadata(
    id: str = Query(...),
) -> dict[str, Any]:
    deployment = deployments.get(id)

    if deployment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment not found: {id}",
        )

    print(f"Deployment metadata requested: {id}")
    return deployment


@app.post("/status")
async def update_status(request: Request) -> dict[str, Any]:
    # Your current HTTPX client sends data=..., which means form data.
    form = await request.form()

    deployment_id = str(form.get("deployment_id", ""))
    runtime_state = str(form.get("runtime_state", ""))

    if not deployment_id:
        raise HTTPException(
            status_code=422,
            detail="deployment_id is required",
        )

    if not runtime_state:
        raise HTTPException(
            status_code=422,
            detail="runtime_state is required",
        )

    deployment_statuses[deployment_id] = runtime_state

    print(
        f"Status updated: deployment_id={deployment_id}, "
        f"runtime_state={runtime_state}"
    )

    return {
        "success": True,
        "deployment_id": deployment_id,
        "runtime_state": runtime_state,
    }


@app.get("/status/{deployment_id}")
async def get_status(deployment_id: str) -> dict[str, str]:
    status = deployment_statuses.get(deployment_id)

    if status is None:
        raise HTTPException(
            status_code=404,
            detail="Status not reported yet",
        )

    return {
        "deployment_id": deployment_id,
        "runtime_state": status,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}