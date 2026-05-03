"""Single-song lookup command."""

from __future__ import annotations

from pathlib import Path

from study_system.application.dto import LookupRequest
from study_system.application.services.enrichment_service import EnrichmentService


def run_lookup(
    service: EnrichmentService,
    *,
    title: str,
    artist: str,
    billboard_file: Path,
    include_lyrics: bool,
) -> dict:
    """Run a single-song lookup command."""

    record = service.lookup_song(
        LookupRequest(
            title=title,
            artist=artist,
            billboard_file=billboard_file,
            include_lyrics=include_lyrics,
        )
    )
    return record.to_dict(include_lyrics=include_lyrics)
