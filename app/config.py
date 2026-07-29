"""
Modulo di configurazione centralizzato.

Responsabilità separate:
- configparser: legge, valida strutturalmente e riscrive il file .ini
- pydantic:     valida i valori e li converte nei tipi corretti

Uso:
    from app.config import settings
    settings.sensor.gpio_pin

    # dopo la registrazione dell'area sul backend:
    from app.config import persist_area_id
    persist_area_id("507f1f77bcf86cd799439011")
"""

import configparser
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


# ------------------------------------------------------------------
# Modelli di validazione per ogni sezione del file .ini
# ------------------------------------------------------------------

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    debug: bool = False


class SensorSettings(BaseModel):
    gpio_pin: int = Field(..., ge=0, le=27)
    poll_interval_seconds: float = Field(..., gt=0)
    threshold_temperature: float
    threshold_humidity: float = Field(..., ge=0, le=100)


class AreaSettings(BaseModel):
    name: str
    beacon_mac: str
    danger_index_threshold: float
    ip_raspberry: str
    # vuoto finché la registrazione automatica non lo valorizza al primo avvio
    area_id: str = ""


class ExternalApiSettings(BaseModel):
    base_url: str
    timeout_seconds: int = Field(..., gt=0)


class RabbitMQSettings(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    username: str
    password: str


class LoggingSettings(BaseModel):
    level: str = "INFO"
    log_file: str = "logs/sensor_service.log"


# ------------------------------------------------------------------
# Contenitore generale
# ------------------------------------------------------------------

class Settings(BaseModel):
    server: ServerSettings
    sensor: SensorSettings
    area: AreaSettings
    external_api: ExternalApiSettings
    rabbitmq: RabbitMQSettings
    logging: LoggingSettings


REQUIRED_SECTIONS = ["server", "sensor", "area", "external_api", "rabbitmq", "logging"]

# Percorso di default, riusato sia da load_settings() che da persist_area_id()
_DEFAULT_CONFIG_PATH = "config.ini"


def load_settings(config_path: str = _DEFAULT_CONFIG_PATH) -> Settings:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File di configurazione non trovato: {config_path}. "
            f"Copia config.ini.example in config.ini e valorizzalo."
        )

    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    missing = [s for s in REQUIRED_SECTIONS if s not in parser]
    if missing:
        raise ValueError(f"Sezioni mancanti in {config_path}: {missing}")

    try:
        return Settings(
            server=ServerSettings(**dict(parser["server"])),
            sensor=SensorSettings(**dict(parser["sensor"])),
            area=AreaSettings(**dict(parser["area"])),
            external_api=ExternalApiSettings(**dict(parser["external_api"])),
            rabbitmq=RabbitMQSettings(**dict(parser["rabbitmq"])),
            logging=LoggingSettings(**dict(parser["logging"])),
        )
    except ValidationError as e:
        raise SystemExit(f"Configurazione non valida in {config_path}:\n{e}")


def persist_area_id(area_id: str, config_path: str = _DEFAULT_CONFIG_PATH) -> None:
    """
    Scrive l'area_id ottenuto dal backend (dopo ricerca/creazione) nella
    sezione [area] di config.ini, così che ai riavvii successivi il
    servizio possa saltare la ricerca per nome e verificare direttamente
    l'esistenza dell'area con GET /api/areas/{area_id}.

    Aggiorna sia il file su disco sia l'istanza `settings` già in memoria,
    per evitare di dover ricaricare la configurazione a runtime.

    NOTA: configparser non preserva i commenti nel file .ini quando lo
    riscrive. Se in futuro serve mantenerli, l'alternativa è una
    sostituzione testuale mirata della sola riga `area_id = ...` con
    una regex, invece di un write() completo del parser.
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    if "area" not in parser:
        raise ValueError(f"Sezione [area] mancante in {config_path}")

    parser["area"]["area_id"] = area_id

    with open(path, "w", encoding="utf-8") as f:
        parser.write(f)

    # aggiorna anche l'istanza già caricata in memoria, senza ricaricare da file
    settings.area.area_id = area_id

    logger = logging.getLogger(__name__)
    logger.info(f"area_id persistito in {config_path}: {area_id}")


# Istanza singleton, caricata all'import
settings = load_settings()

# Configurazione logging di base, centralizzata qui
logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def persist_thresholds(
    threshold_temperature: float,
    threshold_humidity: float,
    danger_index_threshold: float,
    config_path: str = _DEFAULT_CONFIG_PATH,
) -> None:
    """
    Scrive le soglie aggiornate (ricevute via PUT /api/thresholds dal
    backend, coerente con ThresholdUpdateDTO a 3 campi) nelle sezioni
    [sensor] e [area] di config.ini, così che sopravvivano a un riavvio
    del servizio.
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"File di configurazione non trovato: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    if "sensor" not in parser:
        raise ValueError(f"Sezione [sensor] mancante in {config_path}")
    if "area" not in parser:
        raise ValueError(f"Sezione [area] mancante in {config_path}")

    parser["sensor"]["threshold_temperature"] = str(threshold_temperature)
    parser["sensor"]["threshold_humidity"] = str(threshold_humidity)
    parser["area"]["danger_index_threshold"] = str(danger_index_threshold)

    with open(path, "w", encoding="utf-8") as f:
        parser.write(f)

    settings.sensor.threshold_temperature = threshold_temperature
    settings.sensor.threshold_humidity = threshold_humidity
    settings.area.danger_index_threshold = danger_index_threshold

    logger = logging.getLogger(__name__)
    logger.info(
        f"Soglie persistite in {config_path}: "
        f"T>{threshold_temperature}°C  U>{threshold_humidity}%  "
        f"dangerIndex>{danger_index_threshold}"
    )