"""HTTP client helpers."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen


LOGGER = logging.getLogger(__name__)


@dataclass
class JsonHttpClient:
    """Minimal JSON HTTP client with per-key rate limiting.

    :param user_agent: User agent header sent with requests.
    """

    user_agent: str
    _last_request_at: dict[str, float] = field(default_factory=dict)

    def fetch_json(self, url: str, *, rate_limit_key: str | None = None, min_interval: float = 0.0) -> dict[str, Any]:
        """Fetch JSON from a URL.

        :param url: Request URL.
        :param rate_limit_key: Optional key for per-provider throttling.
        :param min_interval: Minimum seconds between requests sharing the key.
        :returns: Parsed JSON payload.
        """

        if rate_limit_key is not None:
            elapsed = time.monotonic() - self._last_request_at.get(rate_limit_key, 0.0)
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

        LOGGER.debug("Fetching JSON from %s", url)
        request = Request(url, headers={"Accept": "application/json", "User-Agent": self.user_agent})
        with urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")

        if rate_limit_key is not None:
            self._last_request_at[rate_limit_key] = time.monotonic()
        return json.loads(payload)
