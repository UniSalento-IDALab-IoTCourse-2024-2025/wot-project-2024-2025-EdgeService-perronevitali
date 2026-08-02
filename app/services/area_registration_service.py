import logging

from app.config import settings, persist_area_id
from app.dto.area_dto import AreaDTO, AreaResponseDTO, AREA_RESULT_OK
from app.services.external_api_service import external_api_service

logger = logging.getLogger(__name__)


async def _find_area_by_beacon(beacon_mac: str) -> AreaDTO | None:
    response = await external_api_service.get("/areas/by-beacon", params={"mac": beacon_mac})
    response.raise_for_status()
    data = AreaResponseDTO.model_validate(response.json())

    if data.result == AREA_RESULT_OK and data.areas and data.areas.areasList:
        return data.areas.areasList[0]

    logger.warning(f"Nessuna area trovata per beaconMAC={beacon_mac} (result={data.result})")
    return None


async def ensure_area_registered() -> str:
    beacon_mac = settings.area.beacon_mac

    try:
        found = await _find_area_by_beacon(beacon_mac)
    except Exception as e:
        logger.warning(f"Backend non raggiungibile per l'handshake beaconMAC={beacon_mac}: {e}")
        if settings.area.area_id:
            logger.warning(
                f"Uso l'area_id già persistito in config.ini come fallback: "
                f"{settings.area.area_id}"
            )
            return settings.area.area_id
        raise

    if found is not None:
        if found.id != settings.area.area_id:
            persist_area_id(found.id)
        logger.info(f"Area risolta per beaconMAC {beacon_mac}: area_id={found.id}")
        return found.id

    raise RuntimeError(
        f"Nessuna area registrata sul backend con beaconMAC={beacon_mac}. "
        f"Un admin deve creare l'area dalla dashboard con lo stesso beaconMAC "
        f"configurato in config.ini."
    )