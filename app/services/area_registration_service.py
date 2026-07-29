"""
Gestisce la risoluzione dell'area sul backend all'avvio del servizio.

Strategia:
1. Chiama GET /api/areas/by-beacon?mac={beaconMAC} — è l'unico endpoint
   pensato per questo handshake ed è pubblico (nessun JWT richiesto),
   a differenza di GET /api/areas/ e GET /api/areas/{id} che richiedono
   ruolo ADMIN/WORKER.
2. Se l'area viene trovata, l'area_id ottenuto viene persistito in
   config.ini (solo se diverso da quello già presente).
3. Se l'area NON viene trovata, il Raspberry Pi NON la crea da sé:
   POST /api/areas/ richiede ruolo ADMIN, che questo servizio non ha e
   non deve avere. L'area va creata da un admin dalla dashboard,
   specificando lo stesso beaconMAC configurato qui in config.ini.
   In questo caso, se in config.ini è già presente un area_id da un
   avvio precedente, viene usato come fallback (utile se il backend è
   temporaneamente irraggiungibile); altrimenti la registrazione fallisce
   e main.py la ritenterà secondo la propria policy di retry.
"""

import logging

from app.config import settings, persist_area_id
from app.dto.area_dto import AreaDTO, AreaResponseDTO, AREA_RESULT_OK
from app.services.external_api_service import external_api_service

logger = logging.getLogger(__name__)


async def _find_area_by_beacon(beacon_mac: str) -> AreaDTO | None:
    """GET /api/areas/by-beacon?mac= — pubblico, handshake del Raspberry Pi."""
    response = await external_api_service.get("/areas/by-beacon", params={"mac": beacon_mac})
    response.raise_for_status()
    data = AreaResponseDTO.model_validate(response.json())

    if data.result == AREA_RESULT_OK and data.areas and data.areas.areasList:
        return data.areas.areasList[0]

    logger.warning(f"Nessuna area trovata per beaconMAC={beacon_mac} (result={data.result})")
    return None


async def ensure_area_registered() -> str:
    """
    Punto di ingresso principale, da chiamare all'avvio del servizio
    prima di iniziare il loop di polling. Ritorna l'area_id.
    """
    beacon_mac = settings.area.beacon_mac
    found = await _find_area_by_beacon(beacon_mac)

    if found is not None:
        if found.id != settings.area.area_id:
            persist_area_id(found.id)
        logger.info(f"Area risolta per beaconMAC {beacon_mac}: area_id={found.id}")
        return found.id

    if settings.area.area_id:
        logger.warning(
            f"Area non trovata sul backend per beaconMAC={beacon_mac} — "
            f"uso l'area_id già persistito in config.ini come fallback: "
            f"{settings.area.area_id}"
        )
        return settings.area.area_id

    raise RuntimeError(
        f"Nessuna area registrata sul backend con beaconMAC={beacon_mac}. "
        f"Un admin deve creare l'area dalla dashboard con lo stesso beaconMAC "
        f"configurato in config.ini."
    )