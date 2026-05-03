"""Integration tests for the enrichment and export pipeline."""

from __future__ import annotations

from pathlib import Path

from study_system.application.dto import LookupRequest
from study_system.application.services.enrichment_service import EnrichmentService
from study_system.application.services.export_service import ExportService
from study_system.domain.models import LyricAsset, MetadataSummary
from study_system.infrastructure.persistence.repositories import JsonSongRepository
from study_system.infrastructure.providers.chart_source import BillboardChartSource


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "hot-100-sample.csv"


class FakeMetadataProvider:
    def lookup_metadata(self, title: str, artist: str) -> MetadataSummary:
        return MetadataSummary(
            matched=True,
            matched_title=title,
            matched_artist=artist,
            first_release_year=1988,
            genres=["pop"],
            songwriters=["Tracy Chapman"],
            producers=["David Kershenbaum"],
            labels=["Elektra"],
            writer_count=1,
            producer_count=1,
            is_cover=False,
            has_sample=False,
            search_query={"title": title, "artist": artist},
        )


class FakeLyricsProvider:
    def lookup_lyrics(self, title: str, artist: str, metadata: MetadataSummary) -> LyricAsset:
        return LyricAsset(
            found=True,
            source="fixture",
            source_url="https://example.test/lyrics",
            query_title=title,
            query_artist=artist,
            lyrics="Fast car\nFast car\nYou got a fast car",
        )


def test_enrichment_and_export_pipeline(tmp_path: Path) -> None:
    service = EnrichmentService(
        chart_source=BillboardChartSource(FIXTURE),
        metadata_provider=FakeMetadataProvider(),
        lyrics_provider=FakeLyricsProvider(),
    )
    record = service.lookup_song(
        LookupRequest(
            title="Fast Car",
            artist="Tracy Chapman",
            billboard_file=FIXTURE,
            include_lyrics=True,
        )
    )
    assert record.title == "Fast Car"
    assert record.chart_rank == 6
    assert record.lyric_features is not None

    repo = JsonSongRepository()
    records_path = tmp_path / "records.json"
    repo.save_records(records_path, [record], include_lyrics=True)
    payload = records_path.read_text(encoding="utf-8")
    assert '"lyrics_text"' in payload
    reloaded = repo.load_records(records_path)
    assert reloaded[0].song_id == record.song_id
    assert reloaded[0].lyrics_text == record.lyrics_text

    csv_path = tmp_path / "final.csv"
    ExportService().export_flat_records_csv(csv_path, reloaded)
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert "Fast Car" in text
    assert "lyrics_text" in text
