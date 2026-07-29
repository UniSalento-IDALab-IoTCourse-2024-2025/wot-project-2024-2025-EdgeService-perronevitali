"""
Entry point del servizio edge FARO.
Ogni istanza gira su un Raspberry Pi dedicato a una specifica area
dell'impianto di stoccaggio.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.services.sensor_service import sensor_service
from app.services.rabbitmq_service import rabbitmq_service
from app.services.area_registration_service import ensure_area_registered
from app.routers import threshold_router
from app.constants import AREA_STATUS_ALERT

logger = logging.getLogger(__name__)

_REGISTRATION_RETRY_DELAYS = [5, 10, 20, 30, 60]  # secondi


async def register_area_with_retry() -> str | None:
    for attempt, delay in enumerate([0] + _REGISTRATION_RETRY_DELAYS, start=1):
        if delay:
            logger.warning(
                f"Registrazione area fallita — nuovo tentativo tra {delay}s "
                f"(tentativo {attempt}/{len(_REGISTRATION_RETRY_DELAYS) + 1})"
            )
            await asyncio.sleep(delay)

        try:
            area_id = await ensure_area_registered()
            logger.info(f"Area registrata correttamente: area_id={area_id}")
            return area_id
        except Exception:
            logger.exception("Errore durante la registrazione dell'area")

    logger.error(
        "Registrazione area non riuscita dopo tutti i tentativi — "
        "il servizio parte comunque ma il polling resta disattivo"
    )
    return None


async def sensor_polling_loop(area_id: str | None) -> None:
    """
    Loop continuo: legge il DHT11 ogni poll_interval_seconds, pubblica
    ogni lettura su faro.sensors e, quando lo stato dell'area cambia
    (OK <-> ALERT), pubblica AREA_ALERT/AREA_SAFE direttamente su
    faro.areas — senza passare dal backend, per garantire la massima
    velocità di notifica ai worker sottoscritti al topic dell'area.
    """
    interval = settings.sensor.poll_interval_seconds

    while area_id is None:
        logger.warning(
            "area_id non disponibile — polling in pausa, nuovo tentativo di "
            "registrazione tra 60s"
        )
        await asyncio.sleep(60)
        try:
            area_id = await ensure_area_registered()
            logger.info(f"Area registrata correttamente: area_id={area_id}")
        except Exception:
            logger.exception("Errore durante la registrazione dell'area")

    while True:
        try:
            reading = await asyncio.to_thread(sensor_service.read_value)

            if reading is None:
                logger.debug("Lettura sensore fallita, riprovo al prossimo ciclo")
            else:
                temperature = reading["temperature"]
                humidity = reading["humidity"]

                await rabbitmq_service.publish_sensor_reading(
                    area_id=area_id, temperature=temperature, humidity=humidity
                )
                logger.info(f"T={temperature:.1f}°C  U={humidity:.1f}%  → pubblicato")

                new_status = sensor_service.evaluate_status_transition(temperature, humidity)
                if new_status is not None:
                    thresholds = sensor_service.get_thresholds()

                    if new_status == AREA_STATUS_ALERT:
                        logger.warning(f"Transizione OK → ALERT per area {area_id}")
                        await rabbitmq_service.publish_area_alert(
                            area_id=area_id,
                            area_name=settings.area.name,
                            status=new_status,
                            current_temperature=temperature,
                            current_humidity=humidity,
                            threshold_temperature=thresholds["threshold_temperature"],
                            threshold_humidity=thresholds["threshold_humidity"],
                        )
                    else:
                        logger.info(f"Transizione ALERT → OK per area {area_id}")
                        await rabbitmq_service.publish_area_safe(
                            area_id=area_id,
                            area_name=settings.area.name,
                            current_temperature=temperature,
                            current_humidity=humidity,
                        )
        except Exception:
            logger.exception("Errore imprevisto nel loop di polling")

        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    await rabbitmq_service.connect()

    area_id = await register_area_with_retry()

    polling_task = asyncio.create_task(sensor_polling_loop(area_id))

    yield  # l'applicazione gira qui

    # --- Shutdown ---
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    await rabbitmq_service.close()


app = FastAPI(title="FARO Edge Service", lifespan=lifespan)

app.include_router(threshold_router.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug,
    )