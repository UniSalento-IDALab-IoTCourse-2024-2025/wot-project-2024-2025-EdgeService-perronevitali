"""
Router che implementa il contratto atteso da
it.unisalento.faro.clients.RaspberryClient (Java):

    PUT /api/thresholds
    GET /api/thresholds

Il backend chiama questi endpoint quando un admin aggiorna le soglie
di un'area dalla dashboard.
"""

import logging

from fastapi import APIRouter

from app.config import persist_thresholds
from app.dto.threshold_dto import ThresholdUpdateDTO
from app.services.sensor_service import sensor_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/thresholds", response_model=ThresholdUpdateDTO)
def get_thresholds():
    current = sensor_service.get_thresholds()
    return ThresholdUpdateDTO(
        thresholdTemperature=current["threshold_temperature"],
        thresholdHumidity=current["threshold_humidity"],
        dangerIndexThreshold=current["danger_index_threshold"],
    )


@router.put("/thresholds", response_model=ThresholdUpdateDTO)
def update_thresholds(dto: ThresholdUpdateDTO):
    sensor_service.update_thresholds(
        threshold_temperature=dto.thresholdTemperature,
        threshold_humidity=dto.thresholdHumidity,
        danger_index_threshold=dto.dangerIndexThreshold,
    )
    persist_thresholds(
        dto.thresholdTemperature,
        dto.thresholdHumidity,
        dto.dangerIndexThreshold,
    )

    logger.info(
        f"Soglie aggiornate dal backend: "
        f"T>{dto.thresholdTemperature}°C  U>{dto.thresholdHumidity}%  "
        f"dangerIndex>{dto.dangerIndexThreshold}"
    )
    return dto