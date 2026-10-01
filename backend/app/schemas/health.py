from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall service status")
    project: str = Field(default="MachIntel", description="Project name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Operating environment")
    timestamp: datetime = Field(description="UTC timestamp of the health check")


class DatabaseHealthResponse(BaseModel):
    status: str = Field(description="Database connectivity status: healthy or degraded")
    database: str = Field(description="Connection state: connected or disconnected")
    latency_ms: Optional[float] = Field(None, description="Roundtrip query latency in milliseconds")
    timestamp: datetime = Field(description="UTC timestamp of the health check")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
