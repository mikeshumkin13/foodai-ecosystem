from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from vision_service.image_loading import VisionImageLoadError, load_prepared_image
from vision_service.inference import FoodRecognitionModel, get_food_recognition_model
from vision_service.schemas import AnalyzeRequest, AnalyzeResponse, DetectedItem, HealthResponse

app = FastAPI(
    title="FoodAI Vision Service",
    description="Internal service for food image analysis with pluggable model inference.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(
    payload: AnalyzeRequest,
    model: Annotated[FoodRecognitionModel, Depends(get_food_recognition_model)],
) -> AnalyzeResponse:
    try:
        image = load_prepared_image(payload.object_reference)
        predictions = model.predict(image)
    except VisionImageLoadError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "vision_model_invalid_response"},
        ) from exc

    return AnalyzeResponse(
        items=[
            DetectedItem(label=prediction.label, confidence=prediction.confidence)
            for prediction in predictions
        ],
    )
