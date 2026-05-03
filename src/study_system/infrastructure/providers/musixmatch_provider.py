"""Musixmatch lyrics adapter."""

from __future__ import annotations

import re
from urllib.parse import urlencode

from study_system.domain.feature_rules import lyrics_candidate_pairs
from study_system.domain.models import LyricAsset, MetadataSummary
from study_system.infrastructure.http.client import JsonHttpClient
from study_system.infrastructure.persistence.cache_store import JsonCacheStore

MUSIXMATCH_ROOT = "https://api.musixmatch.com/ws/1.1"
MUSIXMATCH_RATE_LIMIT_KEY = "musixmatch"


class MusixmatchLyricsProvider:
    """Fetch lyrics from Musixmatch using a licensed API key."""

    def __init__(
        self,
        http_client: JsonHttpClient,
        api_key: str,
        cache_store: JsonCacheStore | None = None,
    ) -> None:
        self.http_client = http_client
        self.api_key = api_key
        self.cache_store = cache_store

    def _fetch_json(self, url: str) -> dict:
        if self.cache_store is not None:
            cached = self.cache_store.get(url)
            if cached is not None:
                return cached
        payload = self.http_client.fetch_json(
            url,
            rate_limit_key=MUSIXMATCH_RATE_LIMIT_KEY,
            min_interval=0.25,
        )
        if self.cache_store is not None:
            self.cache_store.set(url, payload)
        return payload

    def lookup_lyrics(self, title: str, artist: str, metadata: MetadataSummary) -> LyricAsset:
        """Lookup lyric text for a single song."""

        for candidate_title, candidate_artist in lyrics_candidate_pairs(
            title,
            artist,
            metadata.matched_title,
            metadata.matched_artist,
        ):
            track = self._match_track(candidate_title, candidate_artist)
            if not track:
                continue
            track_id = track.get("track_id")
            if track_id is None:
                continue
            source_url = str(track.get("track_share_url") or track.get("track_edit_url") or "")
            lyrics = self._get_lyrics_text(str(track_id))
            if lyrics:
                return LyricAsset(
                    found=True,
                    source="musixmatch",
                    source_url=source_url or None,
                    query_title=candidate_title,
                    query_artist=candidate_artist,
                    lyrics=lyrics,
                )

        return LyricAsset(found=False, source="musixmatch", source_url=None)

    def _match_track(self, title: str, artist: str) -> dict | None:
        params = urlencode(
            {
                "q_track": title,
                "q_artist": artist,
                "f_has_lyrics": 1,
                "apikey": self.api_key,
            }
        )
        payload = self._fetch_json(f"{MUSIXMATCH_ROOT}/matcher.track.get?{params}")
        return payload.get("message", {}).get("body", {}).get("track")

    def _get_lyrics_text(self, track_id: str) -> str | None:
        lyrics = self._track_lyrics_get(track_id)
        if lyrics:
            return lyrics
        return self._track_dump_get(track_id)

    def _track_lyrics_get(self, track_id: str) -> str | None:
        params = urlencode({"track_id": track_id, "apikey": self.api_key})
        payload = self._fetch_json(f"{MUSIXMATCH_ROOT}/track.lyrics.get?{params}")
        lyrics = payload.get("message", {}).get("body", {}).get("lyrics", {})
        text = lyrics.get("lyrics_body")
        return self._clean_lyrics(text)

    def _track_dump_get(self, track_id: str) -> str | None:
        params = urlencode({"track_id": track_id, "apikey": self.api_key})
        payload = self._fetch_json(f"{MUSIXMATCH_ROOT}/track.dump.get?{params}")
        body = payload.get("message", {}).get("body", [])
        if isinstance(body, list) and body:
            text = body[0].get("lyrics")
            return self._clean_lyrics(text)
        return None

    def _clean_lyrics(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        text = re.sub(r"\*{3,}.*$", "", text, flags=re.DOTALL).strip()
        return text or None
