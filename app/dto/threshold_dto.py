from pydantic import BaseModel


class ThresholdUpdateDTO(BaseModel):
    thresholdTemperature: float
    thresholdHumidity: float
    dangerIndexThreshold: float