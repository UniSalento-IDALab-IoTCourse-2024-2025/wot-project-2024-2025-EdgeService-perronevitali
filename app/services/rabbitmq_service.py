import logging
from datetime import datetime, timezone

import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractExchange

from app.config import settings
from app.constants import (
    EXCHANGE_SENSORS,
    EXCHANGE_AREAS,
    ROUTING_KEY_SENSORS,
    MESSAGE_TYPE_SENSOR_READING,
    MESSAGE_TYPE_AREA_ALERT,
    MESSAGE_TYPE_AREA_SAFE,
    area_routing_key,
)
from app.dto.sensor_reading_dto import SensorReadingUpdateDTO
from app.dto.area_message_dto import FaroMessage, AreaAlertPayload, AreaSafePayload

logger = logging.getLogger(__name__)


class RabbitMQService:
    def __init__(self):
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._sensors_exchange: AbstractExchange | None = None
        self._areas_exchange: AbstractExchange | None = None

    async def connect(self) -> None:
        logger.info(
            f"Connessione a RabbitMQ {settings.rabbitmq.host}:{settings.rabbitmq.port}..."
        )
        self._connection = await aio_pika.connect_robust(
            host=settings.rabbitmq.host,
            port=settings.rabbitmq.port,
            login=settings.rabbitmq.username,
            password=settings.rabbitmq.password,
        )
        self._channel = await self._connection.channel()

        self._sensors_exchange = await self._channel.declare_exchange(
            EXCHANGE_SENSORS, ExchangeType.DIRECT, durable=True,
        )
        self._areas_exchange = await self._channel.declare_exchange(
            EXCHANGE_AREAS, ExchangeType.TOPIC, durable=True,
        )

        logger.info("Connessione RabbitMQ stabilita, exchange dichiarati")

    async def close(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Connessione RabbitMQ chiusa")

    # Letture sensore

    async def publish_sensor_reading(
        self, area_id: str, temperature: float, humidity: float
    ) -> None:
        if self._sensors_exchange is None:
            logger.error("RabbitMQ non connesso — impossibile pubblicare la lettura")
            return

        dto = SensorReadingUpdateDTO(
            areaId=area_id,
            temperature=temperature,
            humidity=humidity,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        message = Message(
            body=dto.model_dump_json().encode("utf-8"),
            content_type="application/json",
            type=MESSAGE_TYPE_SENSOR_READING,
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
        )

        await self._sensors_exchange.publish(message, routing_key=ROUTING_KEY_SENSORS)
        logger.debug(f"Lettura pubblicata: T={temperature:.1f}°C U={humidity:.1f}%")

    # Allarmi per area (faro.areas)

    async def _publish_area_message(self, area_id: str, message_type: str, faro_message: FaroMessage) -> None:
        if self._areas_exchange is None:
            logger.error("RabbitMQ non connesso — impossibile pubblicare il messaggio d'area")
            return

        message = Message(
            body=faro_message.model_dump_json().encode("utf-8"),
            content_type="application/json",
            type=message_type,
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        await self._areas_exchange.publish(message, routing_key=area_routing_key(area_id))
        logger.info(f"Messaggio {message_type} pubblicato su area.{area_id}")

    async def publish_area_alert(
        self,
        area_id: str,
        area_name: str,
        status: int,
        current_temperature: float,
        current_humidity: float,
        threshold_temperature: float,
        threshold_humidity: float,
    ) -> None:
        payload = AreaAlertPayload(
            areaId=area_id,
            areaName=area_name,
            status=status,
            currentTemperature=current_temperature,
            currentHumidity=current_humidity,
            thresholdTemperature=threshold_temperature,
            thresholdHumidity=threshold_humidity,
        )
        faro_message = FaroMessage.create(MESSAGE_TYPE_AREA_ALERT, payload)
        await self._publish_area_message(area_id, MESSAGE_TYPE_AREA_ALERT, faro_message)

    async def publish_area_safe(
        self,
        area_id: str,
        area_name: str,
        current_temperature: float,
        current_humidity: float,
    ) -> None:
        payload = AreaSafePayload(
            areaId=area_id,
            areaName=area_name,
            currentTemperature=current_temperature,
            currentHumidity=current_humidity,
        )
        faro_message = FaroMessage.create(MESSAGE_TYPE_AREA_SAFE, payload)
        await self._publish_area_message(area_id, MESSAGE_TYPE_AREA_SAFE, faro_message)


rabbitmq_service = RabbitMQService()