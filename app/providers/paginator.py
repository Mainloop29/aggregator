import logging
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class EventsClientProtocol(Protocol):
    async def events(
        self,
        changed_at: date | datetime,
        next_url: str | None = None,
    ) -> dict[str, Any]: ...


class EventsPaginator:
    def __init__(
        self,
        client: EventsClientProtocol,
        changed_at: date | datetime,
        max_pages: int = 10_000,
    ) -> None:
        self._client = client
        self._changed_at = changed_at
        self._max_pages = max_pages

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        seen_urls: set[str] = set()
        response = await self._client.events(self._changed_at)
        page = 1
        total = 0

        while True:
            results = response.get("results") or []
            for event in results:
                yield event
            total += len(results)

            next_url = response.get("next")
            if not next_url or not results:
                break

            if next_url in seen_urls:
                logger.warning(
                    "Pagination loop detected: next_url=%s already seen (page=%s)",
                    next_url,
                    page,
                )
                break
            seen_urls.add(next_url)

            page += 1
            if page > self._max_pages:
                logger.warning("Pagination exceeded max_pages=%s", self._max_pages)
                break

            logger.debug("Fetch events page=%s next_url=%s", page, next_url)
            response = await self._client.events(self._changed_at, next_url=next_url)

        logger.info("Paginator finished: pages=%s events=%s", page, total)
