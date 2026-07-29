"""
Servizio di lettura del sensore DHT11.

Istanziato come singleton (sensor_service, in fondo al file) così che:
- le soglie possano essere aggiornate a runtime da PUT /api/thresholds
  senza dover ricreare l'oggetto o riavviare il servizio
- lo stato corrente dell'area (OK/ALERT) sia tracciato in un unico posto,
  condiviso tra il loop di polling e il router delle soglie
"""

import logging
import threading

import adafruit_dht
import board

from app.config import settings
from app.constants import AREA_STATUS_OK, AREA_STATUS_ALERT

logger = logging.getLogger(__name__)

_PIN_MAP = {
    4:  board.D4,  17: board.D17, 27: board.D27, 22: board.D22,
    5:  board.D5,  6:  board.D6,  13: board.D13, 19: board.D19,
    26: board.D26, 18: board.D18, 23: board.D23, 24: board.D24,
    25: board.D25, 12: board.D12, 16: board.D16, 20: board.D20,
    21: board.D21,
}


class SensorService:
    def __init__(self, gpio_pin: int | None = None):
        pin_number = gpio_pin if gpio_pin is not None else settings.sensor.gpio_pin
        pin = _PIN_MAP.get(pin_number)

        if pin is None:
            raise ValueError(
                f"GPIO{pin_number} non supportato. Pin validi: {list(_PIN_MAP.keys())}"
            )

        self._dht = adafruit_dht.DHT11(pin)

        # Soglie mutabili a runtime — inizializzate da config.ini,
        # aggiornabili via PUT /api/thresholds
        self._lock = threading.Lock()
        self._threshold_temperature = settings.sensor.threshold_temperature
        self._threshold_humidity = settings.sensor.threshold_humidity
        # dangerIndexThreshold non concorre alla transizione OK/ALERT qui
        # (è usato dal backend per la formula di rischio delle task), ma
        # va comunque tracciato e restituito perché ThresholdUpdateDTO lo
        # include e il backend lo sincronizza insieme alle altre soglie
        self._danger_index_threshold = settings.area.danger_index_threshold

        # Stato corrente dell'area, per rilevare le transizioni OK<->ALERT
        self._current_status = AREA_STATUS_OK

    # -- Lettura --------------------------------------------------------

    def read_value(self) -> dict | None:
        """
        Ritorna {'temperature': float, 'humidity': float} oppure None
        se la lettura fallisce (comune e normale per il DHT11).
        """
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

    # -- Soglie -----------------------------------------------------------

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

    # -- Stato area / transizioni -----------------------------------------

    def get_current_status(self) -> int:
        with self._lock:
            return self._current_status

    def evaluate_status_transition(self, temperature: float, humidity: float) -> int | None:
        """
        Calcola il nuovo stato (OK/ALERT) in base alla lettura corrente.
        Ritorna il nuovo stato SOLO se è cambiato rispetto al precedente
        (stesso criterio del backend: notifica solo sulle transizioni),
        altrimenti ritorna None.
        """
        anomalous = self.is_anomalous(temperature, humidity)
        new_status = AREA_STATUS_ALERT if anomalous else AREA_STATUS_OK

        with self._lock:
            if new_status == self._current_status:
                return None
            self._current_status = new_status
            return new_status


# Istanza singleton — condivisa tra loop di polling e router delle soglie
sensor_service = SensorService()