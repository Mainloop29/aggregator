import json
from datetime import UTC, date, datetime

import httpx
import pytest

from app.providers.events_provider import EventsProviderClient, EventsProviderError


def _client(handler) -> EventsProviderClient:
    return EventsProviderClient(
        base_url="http://provider.test",
        api_key="test-key",
        max_retries=3,
        retry_backoff=0.0,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_events_sends_date_only_and_api_key_header():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"next": None, "results": [{"id": "e1"}]})

    data = await _client(handler).events(datetime(2026, 1, 1, 10, 30, tzinfo=UTC))

    assert data["results"][0]["id"] == "e1"
    assert captured["url"] == "http://provider.test/api/events/?changed_at=2026-01-01"
    assert captured["api_key"] == "test-key"


@pytest.mark.asyncio
async def test_events_accepts_plain_date():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"next": None, "results": []})

    await _client(handler).events(date(2000, 1, 1))
    assert "changed_at=2000-01-01" in captured["url"]


@pytest.mark.asyncio
async def test_events_uses_next_url_verbatim():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"next": None, "results": []})

    next_url = "http://provider.test/api/events/?changed_at=2000-01-01&cursor=xyz"
    await _client(handler).events(date(2000, 1, 1), next_url=next_url)

    assert captured["url"] == next_url


@pytest.mark.asyncio
async def test_events_adds_trailing_slash_if_missing():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"next": None, "results": []})

    await _client(handler)._request("GET", "/api/events")
    assert captured["url"] == "http://provider.test/api/events/"


@pytest.mark.asyncio
async def test_events_raises_with_status_code_on_400():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"changed_at": ["Enter a valid date."]})

    with pytest.raises(EventsProviderError) as exc_info:
        await _client(handler).events(date(2000, 1, 1))

    assert exc_info.value.status_code == 400
    assert exc_info.value.payload == {"changed_at": ["Enter a valid date."]}


@pytest.mark.asyncio
async def test_events_raises_on_401():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid API key"})

    with pytest.raises(EventsProviderError) as exc_info:
        await _client(handler).events(date(2000, 1, 1))

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_seats_parses_seats_key():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={"seats": ["A1", "A3", "B15"]})

    seats = await _client(handler).seats("550e8400-e29b-41d4-a716-446655440000")

    assert seats == ["A1", "A3", "B15"]
    assert captured["path"] == "/api/events/550e8400-e29b-41d4-a716-446655440000/seats/"


@pytest.mark.asyncio
async def test_seats_raises_on_html_500():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            headers={"content-type": "text/html"},
            text="UnexpectedEventStatus: Event is not published",
        )

    with pytest.raises(EventsProviderError) as exc_info:
        await _client(handler).seats("e1")

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_register_posts_all_required_fields():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"ticket_id": "t-1"})

    ticket_id = await _client(handler).register("e1", "Ivan", "Ivanov", "i@x.com", "A15")

    assert ticket_id == "t-1"
    assert captured["path"] == "/api/events/e1/register/"
    assert captured["body"] == {
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "seat": "A15",
        "email": "i@x.com",
    }


@pytest.mark.asyncio
async def test_register_maps_400_to_rich_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=["This ticket is not available (already sold)."])

    with pytest.raises(EventsProviderError) as exc_info:
        await _client(handler).register("e1", "Ivan", "Ivanov", "i@x.com", "A1")

    assert exc_info.value.status_code == 400
    assert exc_info.value.payload == ["This ticket is not available (already sold)."]


@pytest.mark.asyncio
async def test_register_raises_when_no_ticket_id():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={})

    with pytest.raises(EventsProviderError):
        await _client(handler).register("e1", "Ivan", "Ivanov", "i@x.com", "A1")


@pytest.mark.asyncio
async def test_cancel_sends_ticket_id_in_body():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"success": True})

    await _client(handler).cancel(event_id="e1", ticket_id="t-1")

    assert captured["method"] == "DELETE"
    assert captured["path"] == "/api/events/e1/unregister/"
    assert captured["body"] == {"ticket_id": "t-1"}


@pytest.mark.asyncio
async def test_get_retries_on_5xx_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="temp")
        return httpx.Response(200, json={"seats": ["A1"]})

    client = EventsProviderClient(
        base_url="http://provider.test",
        api_key="k",
        max_retries=3,
        retry_backoff=0.0,
        transport=httpx.MockTransport(handler),
    )
    assert await client.seats("e1") == ["A1"]
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_post_is_not_retried_on_5xx():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500, text="boom")

    client = EventsProviderClient(
        base_url="http://provider.test",
        api_key="k",
        max_retries=5,
        retry_backoff=0.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EventsProviderError):
        await client.register("e1", "Ivan", "Ivanov", "i@x.com", "A1")

    assert calls["n"] == 1  # POST не ретраится
