"""
DTO coerente con it.unisalento.faro.dto.otherDTO.ThresholdUpdateDTO (Java).
"""

from pydantic import BaseModel


class ThresholdUpdateDTO(BaseModel):
    thresholdTemperature: float
    thresholdHumidity: float
    dangerIndexThreshold: float