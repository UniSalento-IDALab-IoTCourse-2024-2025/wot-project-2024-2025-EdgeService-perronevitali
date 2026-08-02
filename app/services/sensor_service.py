import logging
import threading

from app.config import settings
from app.constants import AREA_STATUS_OK, AREA_STATUS_ALERT

logger = logging.getLogger(__name__)

_PIN_MAP = {
    4:  "D4",  17: "D17", 27: "D27", 22: "D22",
    5:  "D5",  6:  "D6",  13: "D13", 19: "D19",
    26: "D26", 18: "D18", 23: "D23", 24: "D24",
    25: "D25", 12: "D12", 16: "D16", 20: "D20",
    21: "D21",
}


class SensorService:
    def __init__(self, gpio_pin: int | None = None):
        self._mock = settings.sensor.mock

        if self._mock:
            self._dht = None
            # valori di partenza neutri, sovrascritti da PUT /api/mock/reading
            self._mock_temperature = 22.0
            self._mock_humidity = 50.0
        else:
            import adafruit_dht
            import board

            pin_number = gpio_pin if gpio_pin is not None else settings.sensor.gpio_pin
            pin_name = _PIN_MAP.get(pin_number)

            if pin_name is None:
                raise ValueError(
                    f"GPIO{pin_number} non supportato. Pin validi: {list(_PIN_MAP.keys())}"
                )

            self._dht = adafruit_dht.DHT11(getattr(board, pin_name))

        # Soglie mutabili a runtime inizializzate da config.ini,
        # aggiornabili via PUT /api/thresholds
        self._lock = threading.Lock()
        self._threshold_temperature = settings.sensor.threshold_temperature
        self._threshold_humidity = settings.sensor.threshold_humidity
        self._danger_index_threshold = settings.area.danger_index_threshold
        self._current_status = AREA_STATUS_OK

    # Lettura

    def read_value(self) -> dict | None:
        if self._mock:
            with self._lock:
                return {
                    "temperature": self._mock_temperature,
                    "humidity": self._mock_humidity,
                }

        try:
            temperature = self._dht.temperature
            humidity = self._dht.humidity

            if temperature is None or humidity is None:
                logger.debug("Lettura sensore incompleta (valore None)")
                return None

            return {"temperature": float(temperature), "humidity": float(humidity)}
        except RuntimeError as e:
            logger.debug(f"Lettura sensore fallita: {e}")
            return None

    def set_mock_reading(self, temperature: float, humidity: float) -> None:
        if not self._mock:
            raise RuntimeError("set_mock_reading chiamato ma questa istanza non è in modalità mock")
        with self._lock:
            self._mock_temperature = temperature
            self._mock_humidity = humidity
        logger.info(f"Lettura mock impostata: T={temperature:.1f}°C  U={humidity:.1f}%")

    # Soglie

    def get_thresholds(self) -> dict:
        with self._lock:
            return {
                "threshold_temperature": self._threshold_temperature,
                "threshold_humidity": self._threshold_humidity,
                "danger_index_threshold": self._danger_index_threshold,
            }

    def update_thresholds(
        self,
        threshold_temperature: float,
        threshold_humidity: float,
        danger_index_threshold: float,
    ) -> None:
        with self._lock:
            self._threshold_temperature = threshold_temperature
            self._threshold_humidity = threshold_humidity
            self._danger_index_threshold = danger_index_threshold
        logger.info(
            f"Soglie aggiornate: T>{threshold_temperature}°C  U>{threshold_humidity}%  "
            f"dangerIndex>{danger_index_threshold}"
        )

    def is_anomalous(self, temperature: float, humidity: float) -> bool:
        with self._lock:
            return (
                temperature > self._threshold_temperature
                or humidity > self._threshold_humidity
            )

    # Stato area

    def get_current_status(self) -> int:
        with self._lock:
            return self._current_status

    def evaluate_status_transition(self, temperature: float, humidity: float) -> int | None:
        anomalous = self.is_anomalous(temperature, humidity)
        new_status = AREA_STATUS_ALERT if anomalous else AREA_STATUS_OK

        with self._lock:
            if new_status == self._current_status:
                return None
            self._current_status = new_status
            return new_status

sensor_service = SensorService()