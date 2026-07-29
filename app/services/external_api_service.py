"""
Client HTTP verso OperationalServiceFARO (backend Java).
Usa httpx in modalità asincrona, coerente con il resto dello stack FastAPI.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ExternalApiService:
    def __init__(self):
        self._base_url = settings.external_api.base_url
        self._timeout = settings.external_api.timeout_seconds

    async def get(self, path: str, params: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            return await client.get(path, params=params)

    async def post(self, path: str, json: dict) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            return await client.post(path, json=json)


external_api_service = ExternalApiService()