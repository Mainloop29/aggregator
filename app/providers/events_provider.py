import asyncio
import logging
from datetime import date, datetime
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EventsProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


class EventsProviderClient:
    IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "DELETE"})

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or settings.events_provider_base_url).rstrip("/")
        self._api_key = api_key if api_key is not None else settings.events_provider_api_key
        self._timeout = timeout or settings.events_provider_timeout
        self._max_retries = max(1, max_retries)
        self._retry_backoff = retry_backoff
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "x-api-key": self._api_key}

    @staticmethod
    def _fmt_date(value: date | datetime) -> str:
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not path.endswith("/"):
            path = f"{path}/"
        return await self._request_url(method, f"{self._base_url}{path}", **kwargs)

    async def _request_url(self, method: str, url: str, **kwargs: Any) -> Any:
        retryable = method.upper() in self.IDEMPOTENT_METHODS
        attempts = self._max_retries if retryable else 1

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                    response = await client.request(method, url, headers=self._headers(), **kwargs)
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                logger.warning(
                    "Network error %s %s (attempt %s/%s): %s",
                    method,
                    url,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(self._retry_backoff * attempt)
                    continue
                raise EventsProviderError(str(exc)) from exc

            # 5xx — потенциально временная, ретраим только идемпотентные методы
            if 500 <= response.status_code < 600 and attempt < attempts:
                logger.warning(
                    "Provider 5xx %s %s (attempt %s/%s)",
                    method,
                    url,
                    attempt,
                    attempts,
                )
                await asyncio.sleep(self._retry_backoff * attempt)
                continue

            # 4xx — бизнес-ошибка, ретраить нельзя
            if 400 <= response.status_code < 500:
                payload = _safe_json(response)
                raise EventsProviderError(
                    f"Provider {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                    payload=payload,
                )

            if response.status_code >= 500:
                payload = _safe_json(response)
                raise EventsProviderError(
                    f"Provider {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                    payload=payload,
                )

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise EventsProviderError("unreachable: retries exhausted")

    # ---------- Events ----------

    async def events(
        self,
        changed_at: date | datetime,
        next_url: str | None = None,
    ) -> dict[str, Any]:

        if next_url:
            return await self._request_url("GET", next_url)
        return await self._request(
            "GET",
            "/api/events/",
            params={"changed_at": self._fmt_date(changed_at)},
        )

    async def event(self, event_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/events/{event_id}/")

    # ---------- Seats ----------

    async def seats(self, event_id: str) -> list[str]:
        data = await self._request("GET", f"/api/events/{event_id}/seats/") or {}
        if isinstance(data, dict):
            return list(data.get("seats") or [])
        if isinstance(data, list):
            return list(data)
        return []

    # ---------- Registration ----------

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        """POST /api/events/{event_id}/register/ -> ticket_id."""
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "seat": seat,
            "email": email,
        }
        data = await self._request("POST", f"/api/events/{event_id}/register/", json=payload) or {}
        ticket_id = data.get("ticket_id")
        if not ticket_id:
            raise EventsProviderError("Provider did not return ticket_id")
        return str(ticket_id)

    async def cancel(self, event_id: str, ticket_id: str) -> None:
        """DELETE /api/events/{event_id}/unregister/ (ticket_id в теле)."""
        await self._request(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )
