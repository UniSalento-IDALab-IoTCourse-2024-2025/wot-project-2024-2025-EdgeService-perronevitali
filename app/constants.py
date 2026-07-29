"""
Costanti condivise con il backend Java.
Tenute manualmente sincronizzate con:
- it.unisalento.faro.configuration.rabbitmq.RabbitMQConstants
- it.unisalento.faro.configuration.rabbitmq.RabbitMQMessageTypes
- it.unisalento.faro.domain.Area (costanti di stato)
"""

# --- Exchange ---
EXCHANGE_SENSORS = "faro.sensors"   # direct — Raspberry Pi pubblica qui
EXCHANGE_AREAS = "faro.areas"       # topic  — notifiche area.{areaId}

# --- Routing key ---
ROUTING_KEY_SENSORS = "sensors"


def area_routing_key(area_id: str) -> str:
    return f"area.{area_id}"


# --- Message type ---
MESSAGE_TYPE_SENSOR_READING = "SENSOR_READING"
MESSAGE_TYPE_AREA_ALERT = "AREA_ALERT"
MESSAGE_TYPE_AREA_SAFE = "AREA_SAFE"

# --- Stato area (coerente con Area.OK / Area.ALERT lato Java) ---
AREA_STATUS_OK = 0
AREA_STATUS_ALERT = 1