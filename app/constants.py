# Exchange
EXCHANGE_SENSORS = "faro.sensors"   # Raspberry Pi pubblica qui
EXCHANGE_AREAS = "faro.areas"       # topic notifiche area.{areaId}

# Routing key
ROUTING_KEY_SENSORS = "sensors"


def area_routing_key(area_id: str) -> str:
    return f"area.{area_id}"


# Message type
MESSAGE_TYPE_SENSOR_READING = "SENSOR_READING"
MESSAGE_TYPE_AREA_ALERT = "AREA_ALERT"
MESSAGE_TYPE_AREA_SAFE = "AREA_SAFE"

MQTT_AREA_SUBTOPIC = {
    MESSAGE_TYPE_AREA_ALERT: "alert",
    MESSAGE_TYPE_AREA_SAFE: "alert",
}


def area_mqtt_topic(area_id: str, message_type: str) -> str:
    return f"area/{area_id}/{MQTT_AREA_SUBTOPIC[message_type]}"


# Stato area
AREA_STATUS_OK = 0
AREA_STATUS_ALERT = 1

# Sliding window per il calcolo della media delle grandezze
WINDOW_SIZE = 3
RECOVERY_CONFIRMATIONS_REQUIRED = 5