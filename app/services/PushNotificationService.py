import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushNotificationService:
    def __init__(self):
        self._user_service_base_url = settings.user_service.base_url
        self._internal_secret = settings.user_service.internal_secret
        self._timeout = settings.user_service.timeout_seconds

    async def _get_push_tokens(self, area_id: str) -> list[str]:
        url = f"{self._user_service_base_url}/users/push-tokens"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    url,
                    params={"areaId": area_id},
                    headers={"X-Internal-Secret": self._internal_secret},
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            logger.exception(f"Errore nel recupero dei push token per l'area {area_id}")
            return []

    async def _send_push(self, tokens: list[str], title: str, body: str) -> None:
        messages = [
            {
                "to": token,
                "title": title,
                "body": body,
                "priority": "high",
                "channelId": "default",
            }
            for token in tokens
            if token
        ]

        if not messages:
            return

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=messages,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                logger.info(f"Expo push response: {response.status_code} {response.text}")
        except Exception:
            logger.exception("Errore nell'invio della push Expo")

    async def notify_area_alert(self, area_id: str, area_name: str) -> None:
        tokens = await self._get_push_tokens(area_id)
        if not tokens:
            return

        await self._send_push(
            tokens,
            title = "PERICOLO AREA",
            body = "PERICOLO RILEVATO, EVACUARE L'AREA",
        )

    async def notify_area_safe(self, area_id: str, area_name: str) -> None:
        tokens = await self._get_push_tokens(area_id)
        if not tokens:
            return

        await self._send_push(
            tokens,
            title = "Pericolo rientrato",
            body = "Il pericolo è rientrato, è possibile tornare nell'area in sicurezza",
        )


push_notification_service = PushNotificationService()