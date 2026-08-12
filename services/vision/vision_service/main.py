from __future__ import annotations

from fastapi import FastAPI

from vision_service.schemas import AnalyzeRequest, AnalyzeResponse, DetectedItem, HealthResponse

app = FastAPI(
    title="FoodAI Vision Service",
    description="Internal service for food image analysis. MVP returns a mock result.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    return AnalyzeResponse(items=[DetectedItem(label="rice", confidence=0.92)])
