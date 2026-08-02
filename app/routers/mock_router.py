import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.sensor_service import sensor_service

logger = logging.getLogger(__name__)

router = APIRouter()


class MockReadingDTO(BaseModel):
    temperature: float
    humidity: float


@router.put("/mock/reading", response_model=MockReadingDTO)
def set_mock_reading(dto: MockReadingDTO):
    if not settings.sensor.mock:
        raise HTTPException(
            status_code=409,
            detail="Questa istanza non è in modalità mock (settings.sensor.mock=false)",
        )

    sensor_service.set_mock_reading(dto.temperature, dto.humidity)
    logger.info(f"Lettura mock forzata via API: T={dto.temperature}°C U={dto.humidity}%")
    return dto