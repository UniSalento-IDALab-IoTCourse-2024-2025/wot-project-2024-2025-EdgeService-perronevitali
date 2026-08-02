from pydantic import BaseModel, Field

AREA_RESULT_OK = 0
AREA_RESULT_NOT_FOUND = 1
AREA_RESULT_DUPLICATE_BEACON = 2
AREA_RESULT_HAS_ACTIVE_TASKS = 3

class AreaDTO(BaseModel):
    id: str | None = None
    name: str
    beaconMAC: str
    thresholdTemperature: float
    thresholdHumidity: float
    dangerIndexThreshold: float
    ipRaspberry: str
    totalDangerIndex: float = 0.0
    status: int = 0
    currentTemperature: float = 0.0
    currentHumidity: float = 0.0
    userIdsInArea: list[str] = Field(default_factory=list)
    unauthorizedWorkerIds: list[str] = Field(default_factory=list)


class AreasListDTO(BaseModel):
    areasList: list[AreaDTO] = Field(default_factory=list)


class AreaResponseDTO(BaseModel):
    result: int
    message: str | None = None
    areas: AreasListDTO | None = None


