"""Unit tests for the JSON HTTP client."""

from __future__ import annotations

from types import SimpleNamespace

import study_system.infrastructure.http.client as client_module
from study_system.infrastructure.http.client import JsonHttpClient


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return b'{"ok": true}'


def test_fetch_json_uses_urlopen(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(client_module, "urlopen", fake_urlopen)
    payload = JsonHttpClient(user_agent="test-agent").fetch_json("https://example.test")
    assert payload == {"ok": True}
