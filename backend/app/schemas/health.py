from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(..., description="Health status", examples=["ok"])
    service: str = Field(..., description="Service name", examples=["Ops Pulse API"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    environment: str = Field(..., description="Runtime environment", examples=["local"])
    request_id: str = Field(..., description="Request trace identifier", examples=["req-123"])
    timestamp: datetime = Field(..., description="Response timestamp (UTC)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "Ops Pulse API",
                "version": "0.1.0",
                "environment": "local",
                "request_id": "req-123",
                "timestamp": "2026-02-22T12:00:00Z",
            }
        }
    )
