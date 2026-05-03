"""Lyrics.ovh adapter."""

from __future__ import annotations

from urllib.error import HTTPError
from urllib.parse import quote

from study_system.domain.feature_rules import lyrics_candidate_pairs
from study_system.domain.models import LyricAsset, MetadataSummary
from study_system.infrastructure.http.client import JsonHttpClient
from study_system.infrastructure.persistence.cache_store import JsonCacheStore

LYRICS_OVH_ROOT = "https://api.lyrics.ovh/v1"


class LyricsOvhProvider:
    """Fetch lyric text from Lyrics.ovh.

    :param http_client: JSON HTTP client.
    :param cache_store: Optional filesystem cache.
    """

    def __init__(self, http_client: JsonHttpClient, cache_store: JsonCacheStore | None = None) -> None:
        self.http_client = http_client
        self.cache_store = cache_store

    def _fetch_json(self, url: str) -> dict:
        if self.cache_store is not None:
            cached = self.cache_store.get(url)
            if cached is not None:
                return cached
        payload = self.http_client.fetch_json(url)
        if self.cache_store is not None:
            compact_payload = {
                "lyrics_text": payload.get("lyrics"),
                "source": "lyrics.ovh",
                "source_url": url,
            }
            self.cache_store.set(url, compact_payload)
        return payload

    def lookup_lyrics(self, title: str, artist: str, metadata: MetadataSummary) -> LyricAsset:
        """Lookup lyric text for a single song."""

        for candidate_title, candidate_artist in lyrics_candidate_pairs(
            title,
            artist,
            metadata.matched_title,
            metadata.matched_artist,
        ):
            url = f"{LYRICS_OVH_ROOT}/{quote(candidate_artist)}/{quote(candidate_title)}"
            try:
                payload = self._fetch_json(url)
            except HTTPError as exc:
                if exc.code == 404:
                    continue
                raise
            lyrics = payload.get("lyrics_text") or payload.get("lyrics")
            if isinstance(lyrics, str) and lyrics.strip():
                return LyricAsset(
                    found=True,
                    source=str(payload.get("source") or "lyrics.ovh"),
                    source_url=str(payload.get("source_url") or url),
                    query_title=candidate_title,
                    query_artist=candidate_artist,
                    lyrics=lyrics.strip(),
                )

        return LyricAsset(found=False, source="lyrics.ovh", source_url=None)
