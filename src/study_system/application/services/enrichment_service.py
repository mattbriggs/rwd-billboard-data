"""Single-song and batch enrichment workflows."""

from __future__ import annotations

import json
import logging
from hashlib import sha1
from urllib.error import HTTPError, URLError

from study_system.application.contracts import ChartSource, LyricsProvider, MetadataProvider
from study_system.application.dto import LookupRequest
from study_system.domain.feature_rules import normalize_text
from study_system.domain.models import MetadataSummary, ProvenanceEntry, SongRecord


LOGGER = logging.getLogger(__name__)


class EnrichmentService:
    """Orchestrate chart, metadata, and lyric enrichment."""

    def __init__(
        self,
        chart_source: ChartSource,
        metadata_provider: MetadataProvider,
        lyrics_provider: LyricsProvider,
    ) -> None:
        self.chart_source = chart_source
        self.metadata_provider = metadata_provider
        self.lyrics_provider = lyrics_provider

    def _song_id(self, title: str, artist: str, year: int | None) -> str:
        seed = f"{normalize_text(title)}::{normalize_text(artist)}::{year or 'unknown'}"
        return sha1(seed.encode("utf-8")).hexdigest()[:12]

    def lookup_song(self, request: LookupRequest) -> SongRecord:
        """Enrich a single song lookup request.

        :param request: Lookup request.
        :returns: Enriched song record.
        """

        errors: list[str] = []
        chart_summary = self.chart_source.lookup_chart_context(request.title, request.artist)
        LOGGER.info("Chart lookup completed", extra={"title": request.title, "artist": request.artist})

        try:
            metadata = self.metadata_provider.lookup_metadata(request.title, request.artist)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"Music metadata lookup failed: {exc}")
            metadata = MetadataSummary(matched=False, search_query={"title": request.title, "artist": request.artist})

        try:
            lyric_asset = self.lyrics_provider.lookup_lyrics(request.title, request.artist, metadata)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"Lyrics lookup failed: {exc}")
            from study_system.domain.models import LyricAsset

            lyric_asset = LyricAsset(found=False, source="lyrics.ovh", source_url=None)

        feature_set = None
        if lyric_asset.lyrics:
            from study_system.domain.feature_rules import lyric_features as compute_lyric_features

            feature_set = compute_lyric_features(request.title, lyric_asset.lyrics)

        matched_title = metadata.matched_title or chart_summary.matched_title or request.title
        matched_artist = metadata.matched_artist or chart_summary.matched_artist or request.artist
        year = chart_summary.peak_year or metadata.first_release_year
        song_id = self._song_id(matched_title, matched_artist, year)
        provenance = [
            ProvenanceEntry(
                field_name="chart_context",
                provider_name="local_billboard_archive",
                source_ref=chart_summary.source_file,
                confidence=1.0 if chart_summary.found else None,
            )
        ]
        if metadata.recording_url:
            provenance.append(
                ProvenanceEntry(
                    field_name="metadata",
                    provider_name="musicbrainz",
                    source_ref=metadata.recording_url,
                )
            )
        if lyric_asset.source_url:
            provenance.append(
                ProvenanceEntry(
                    field_name="lyrics",
                    provider_name=lyric_asset.source,
                    source_ref=lyric_asset.source_url,
                )
            )

        return SongRecord(
            song_id=song_id,
            query_title=request.title,
            query_artist=request.artist,
            title=matched_title,
            artist=matched_artist,
            year=year,
            chart_rank=chart_summary.best_weekly_rank,
            source_chart_list="Billboard Hot 100 weekly archive",
            genre=list(metadata.genres),
            songwriters=list(metadata.songwriters),
            producers=list(metadata.producers),
            label=list(metadata.labels),
            writer_count=metadata.writer_count,
            producer_count=metadata.producer_count,
            is_cover=metadata.is_cover,
            has_sample=metadata.has_sample,
            lyrics_source_url=lyric_asset.source_url,
            lyrics_found=lyric_asset.found,
            recording_length_ms=metadata.recording_length_ms,
            first_release_date=metadata.first_release_date,
            billboard_best_chart_week=chart_summary.best_chart_week,
            billboard_weeks_on_chart_max=chart_summary.weeks_on_chart_max,
            lyric_features=feature_set,
            lyric_asset=lyric_asset if request.include_lyrics else lyric_asset.without_text(),
            metadata_summary=metadata,
            chart_summary=chart_summary,
            provenance=provenance,
            errors=errors,
        )

    def enrich_corpus(self, entries: list[tuple[int, str, str]], include_lyrics: bool, billboard_file) -> list[SongRecord]:
        """Enrich a batch of corpus entries.

        :param entries: ``(year, title, artist)`` tuples.
        :param include_lyrics: Whether to include lyric text.
        :param billboard_file: Billboard CSV path.
        :returns: Enriched song records.
        """

        records: list[SongRecord] = []
        for _, title, artist in entries:
            records.append(
                self.lookup_song(
                    LookupRequest(
                        title=title,
                        artist=artist,
                        billboard_file=billboard_file,
                        include_lyrics=include_lyrics,
                    )
                )
            )
        return records
