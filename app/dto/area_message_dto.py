"""
DTO coerenti con i messaggi pubblicati su faro.areas (topic exchange).
Rispecchiano it.unisalento.faro.dto.messagesDTO.FaroMessage,
AreaAlertMessage e AreaSafeMessage (Java), oltre al formato documentato
in FARO_AMQP_Communication.md.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class AreaAlertPayload(BaseModel):
    areaId: str
    areaName: str
    status: int
    currentTemperature: float
    currentHumidity: float
    thresholdTemperature: float
    thresholdHumidity: float


class AreaSafePayload(BaseModel):
    areaId: str
    areaName: str
    currentTemperature: float
    currentHumidity: float


class FaroMessage(BaseModel):
    """Wrapper generico usato per ogni messaggio su faro.areas / faro.inbox."""
    type: str
    payload: Any
    timestamp: str

    @classmethod
    def create(cls, message_type: str, payload: BaseModel) -> "FaroMessage":
        return cls(
            type=message_type,
            payload=payload.model_dump(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )