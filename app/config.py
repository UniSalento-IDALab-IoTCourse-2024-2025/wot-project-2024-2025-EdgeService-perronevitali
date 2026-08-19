import configparser
import logging
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    debug: bool = False


class SensorSettings(BaseModel):
    gpio_pin: int = Field(..., ge=0, le=27)
    poll_interval_seconds: float = Field(..., gt=0)
    threshold_temperature: float
    threshold_humidity: float = Field(..., ge=0, le=100)
    # true = niente hardware reale, le letture arrivano da PUT /api/mock/reading
    mock: bool = False


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


class UserServiceSettings(BaseModel):
    base_url: str
    internal_secret: str
    timeout_seconds: int = Field(..., gt=0)


class RabbitMQSettings(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    username: str
    password: str


class MqttSettings(BaseModel):
    host: str
    port: int = Field(..., ge=1, le=65535)
    username: str
    password: str


class LoggingSettings(BaseModel):
    level: str = "INFO"
    log_file: str = "logs/sensor_service.log"

class Settings(BaseModel):
    server: ServerSettings
    sensor: SensorSettings
    area: AreaSettings
    external_api: ExternalApiSettings
    user_service: UserServiceSettings
    rabbitmq: RabbitMQSettings
    mqtt: MqttSettings
    logging: LoggingSettings


REQUIRED_SECTIONS = ["server", "sensor", "area", "external_api", "user_service", "rabbitmq", "mqtt", "logging"]
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
            user_service=UserServiceSettings(**dict(parser["user_service"])),
            rabbitmq=RabbitMQSettings(**dict(parser["rabbitmq"])),
            mqtt=MqttSettings(**dict(parser["mqtt"])),
            logging=LoggingSettings(**dict(parser["logging"])),
        )
    except ValidationError as e:
        raise SystemExit(f"Configurazione non valida in {config_path}:\n{e}")


def persist_area_id(area_id: str, config_path: str = _DEFAULT_CONFIG_PATH) -> None:
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

    settings.area.area_id = area_id

    logger = logging.getLogger(__name__)
    logger.info(f"area_id persistito in {config_path}: {area_id}")

settings = load_settings()

logging.basicConfig(
    level=getattr(logging, settings.logging.level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def persist_thresholds(
    threshold_temperature: float,
    threshold_humidity: float,
    danger_index_threshold: float,
    config_path: str = _DEFAULT_CONFIG_PATH,
) -> None:

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