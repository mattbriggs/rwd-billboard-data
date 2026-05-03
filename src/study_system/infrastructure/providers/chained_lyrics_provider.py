"""Composite lyrics provider helpers."""

from __future__ import annotations

import logging

from study_system.application.contracts import LyricsProvider
from study_system.domain.models import LyricAsset, MetadataSummary

LOGGER = logging.getLogger(__name__)


class ChainedLyricsProvider:
    """Try multiple lyrics providers in order until one succeeds."""

    def __init__(self, providers: list[LyricsProvider]) -> None:
        self.providers = providers

    def lookup_lyrics(self, title: str, artist: str, metadata: MetadataSummary) -> LyricAsset:
        """Lookup lyrics by trying each provider in sequence."""

        fallback_asset: LyricAsset | None = None
        for provider in self.providers:
            try:
                asset = provider.lookup_lyrics(title, artist, metadata)
            except Exception as exc:  # pragma: no cover - exercised via CLI integration paths
                LOGGER.warning(
                    "Lyrics provider failed; trying next provider",
                    extra={"provider": provider.__class__.__name__, "title": title, "artist": artist},
                    exc_info=exc,
                )
                continue
            if asset.found:
                return asset
            fallback_asset = asset

        return fallback_asset or LyricAsset(found=False, source="lyrics_chain", source_url=None)
