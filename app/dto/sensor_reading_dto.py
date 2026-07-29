"""
DTO coerente con it.unisalento.faro.dto.otherDTO.SensorReadingUpdateDTO (Java).
I nomi dei campi rispettano il camelCase atteso da Jackson lato backend.
"""

from pydantic import BaseModel


class SensorReadingUpdateDTO(BaseModel):
    areaId: str
    temperature: float
    humidity: float
    timestamp: str  # ISO 8601, es. "2026-07-13T14:32:07.123456+00:00"