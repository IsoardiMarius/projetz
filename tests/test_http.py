from __future__ import annotations

import httpx
import pytest

from radar.polymarket.http import ApiError, HttpClient, RateLimiter


class FakeTime:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_rate_limiter_spaces_calls() -> None:
    t = FakeTime()
    limiter = RateLimiter(4.0, clock=t.clock, sleep=t.sleep)
    for _ in range(3):
        limiter.wait()
    assert t.sleeps == [0.25, 0.25]


def test_rate_limiter_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError, match="strictement positif"):
        RateLimiter(0)


def make_client(handler: httpx.MockTransport, t: FakeTime, **kw: object) -> HttpClient:
    return HttpClient(
        "https://api.example.invalid",
        transport=handler,
        sleep=t.sleep,
        clock=t.clock,
        rate_per_s=1000.0,
        **kw,  # type: ignore[arg-type]
    )


def test_retries_on_429_respecting_retry_after() -> None:
    t = FakeTime()
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        return httpx.Response(200, json={"ok": True})

    client = make_client(httpx.MockTransport(handler), t)
    assert client.get_json("/x") == {"ok": True}
    assert len(calls) == 2
    assert 7.0 in t.sleeps


def test_gives_up_after_max_retries() -> None:
    t = FakeTime()
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(503)), t, max_retries=2)
    with pytest.raises(ApiError, match="3 tentatives"):
        client.get_json("/x")


def test_client_error_is_not_retried() -> None:
    t = FakeTime()
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(400, json={"error": "bad"})

    client = make_client(httpx.MockTransport(handler), t)
    with pytest.raises(ApiError, match="HTTP 400"):
        client.get_json("/x")
    assert len(calls) == 1


def test_query_encoding_user_agent_and_cache_buster() -> None:
    t = FakeTime()
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    client = make_client(httpx.MockTransport(handler), t)
    client.get_json("/m", {"ids": ["a", "b"], "closed": True, "n": 3}, bust_cache=True)
    request = seen[0]
    assert request.url.params.get_list("ids") == ["a", "b"]
    assert request.url.params["closed"] == "true"
    assert request.url.params["n"] == "3"
    assert request.url.params["_"] == str(int(t.now * 1000))
    assert request.headers["User-Agent"].startswith("radar/")


def test_rate_limiter_is_thread_safe() -> None:
    import threading

    slots: list[float] = []
    lock = threading.Lock()
    t = FakeTime()

    def fake_sleep(seconds: float) -> None:
        with lock:
            slots.append(seconds)

    limiter = RateLimiter(10.0, clock=lambda: t.now, sleep=fake_sleep)
    threads = [threading.Thread(target=limiter.wait) for _ in range(20)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    # 20 appels au même instant : 19 attentes distinctes, espacées de 0,1 s.
    assert sorted(round(s, 6) for s in slots) == [round(0.1 * i, 6) for i in range(1, 20)]
