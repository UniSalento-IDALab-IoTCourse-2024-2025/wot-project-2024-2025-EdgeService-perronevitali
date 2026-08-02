from pydantic import BaseModel


class SensorReadingUpdateDTO(BaseModel):
    areaId: str
    temperature: float
    humidity: float
    timestamp: str  # ISO 8601
