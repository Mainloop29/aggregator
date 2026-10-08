from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.providers.paginator import EventsPaginator


@pytest.mark.asyncio
async def test_paginator_follows_next_url_until_none():
    client = AsyncMock()
    page_2 = "http://provider.test/api/events/?changed_at=2000-01-01&cursor=xyz"
    client.events.side_effect = [
        {"next": page_2, "results": [{"id": "e1"}, {"id": "e2"}]},
        {"next": None, "results": [{"id": "e3"}]},
    ]

    collected = [e async for e in EventsPaginator(client, date(2000, 1, 1))]

    assert [e["id"] for e in collected] == ["e1", "e2", "e3"]
    assert client.events.await_count == 2

    first_call = client.events.await_args_list[0]
    second_call = client.events.await_args_list[1]
    assert first_call.args == (date(2000, 1, 1),)
    assert first_call.kwargs == {}
    assert second_call.kwargs == {"next_url": page_2}


@pytest.mark.asyncio
async def test_paginator_stops_when_next_is_none():
    client = AsyncMock()
    client.events.return_value = {"next": None, "results": [{"id": "e1"}]}

    collected = [e async for e in EventsPaginator(client, date(2000, 1, 1))]

    assert [e["id"] for e in collected] == ["e1"]
    assert client.events.await_count == 1


@pytest.mark.asyncio
async def test_paginator_stops_on_empty_results_with_next_present():
    client = AsyncMock()
    client.events.return_value = {
        "next": "http://provider.test/api/events/?cursor=loop",
        "results": [],
    }

    collected = [e async for e in EventsPaginator(client, date(2000, 1, 1))]

    assert collected == []
    assert client.events.await_count == 1


@pytest.mark.asyncio
async def test_paginator_stops_on_repeated_next_url(caplog):
    client = AsyncMock()
    looped = "http://provider.test/api/events/?cursor=loop"
    client.events.side_effect = [
        {"next": looped, "results": [{"id": "e1"}]},
        {"next": looped, "results": [{"id": "e2"}]},
    ]

    collected = [e async for e in EventsPaginator(client, date(2000, 1, 1))]

    assert [e["id"] for e in collected] == ["e1", "e2"]
    assert client.events.await_count == 2
    assert any("Pagination loop detected" in r.message for r in caplog.records)
