"""Pydantic schemas for API."""
from pydantic import BaseModel


class MatchResult(BaseModel):
    """Single match result."""
    image_path: str
    confidence: float
    distance: float


class SearchResponse(BaseModel):
    """Response for search endpoint."""
    success: bool
    matches: list[MatchResult] = []
    error: str | None = None


class HealthResponse(BaseModel):
    """Response for health endpoint."""
    status: str = "ok"
    version: str = "1.0.0"


class RegisterResponse(BaseModel):
    """Response for register endpoint."""
    success: bool
    count: int = 0
    message: str = ""
