"""Export workflows for study records and datasets."""

from __future__ import annotations

from pathlib import Path

from study_system.domain.models import ScoreCard, SongRecord
from study_system.infrastructure.persistence.file_store import write_csv_rows, write_json


class ExportService:
    """Export enriched records and scored datasets."""

    def export_json(self, path: Path, payload, *, pretty: bool = True) -> None:
        """Write arbitrary JSON payloads."""

        write_json(path, payload, pretty=pretty)

    def export_flat_records_csv(self, path: Path, records: list[SongRecord]) -> None:
        """Export a flat CSV of enriched records."""

        rows: list[dict] = []
        for record in records:
            row = {
                "song_id": record.song_id,
                "query_title": record.query_title,
                "query_artist": record.query_artist,
                "title": record.title,
                "artist": record.artist,
                "year": record.year,
                "chart_rank": record.chart_rank,
                "source_chart_list": record.source_chart_list,
                "genre": "; ".join(record.genre),
                "songwriters": "; ".join(record.songwriters),
                "producers": "; ".join(record.producers),
                "label": "; ".join(record.label),
                "writer_count": record.writer_count,
                "producer_count": record.producer_count,
                "is_cover": record.is_cover,
                "has_sample": record.has_sample,
                "lyrics_source_url": record.lyrics_source_url,
                "lyrics_found": record.lyrics_found,
                "lyrics_text": record.lyrics_text,
                "recording_length_ms": record.recording_length_ms,
                "first_release_date": record.first_release_date,
                "billboard_best_chart_week": record.billboard_best_chart_week,
                "billboard_weeks_on_chart_max": record.billboard_weeks_on_chart_max,
            }
            if record.lyric_features is not None:
                row.update(record.lyric_features.to_dict())
            rows.append(row)
        write_csv_rows(path, rows)

    def export_final_dataset(
        self,
        path: Path,
        records: list[SongRecord],
        scores: list[ScoreCard],
        *,
        score_sources: dict[str, str] | None = None,
    ) -> None:
        """Export a final joined dataset with scores."""

        score_map = {score.song_id: score for score in scores}
        score_sources = score_sources or {}
        rows: list[dict] = []
        for record in records:
            row = {
                "song_id": record.song_id,
                "query_title": record.query_title,
                "query_artist": record.query_artist,
                "title": record.title,
                "artist": record.artist,
                "year": record.year,
                "chart_rank": record.chart_rank,
                "source_chart_list": record.source_chart_list,
                "genre": "; ".join(record.genre),
                "songwriters": "; ".join(record.songwriters),
                "producers": "; ".join(record.producers),
                "label": "; ".join(record.label),
                "writer_count": record.writer_count,
                "producer_count": record.producer_count,
                "is_cover": record.is_cover,
                "has_sample": record.has_sample,
                "lyrics_source_url": record.lyrics_source_url,
                "lyrics_found": record.lyrics_found,
                "lyrics_text": record.lyrics_text,
                "recording_length_ms": record.recording_length_ms,
                "first_release_date": record.first_release_date,
                "billboard_best_chart_week": record.billboard_best_chart_week,
                "billboard_weeks_on_chart_max": record.billboard_weeks_on_chart_max,
                "speaker_situation_clarity": None,
                "thematic_unity": None,
                "image_motif_integration": None,
                "structural_development": None,
                "context_independence": None,
                "scorer_id": None,
                "notes": None,
                "self_containment_index": None,
                "score_complete": False,
                "score_source": "missing",
            }
            if record.lyric_features is not None:
                row.update(record.lyric_features.to_dict())
            score = score_map.get(record.song_id)
            if score is not None:
                row.update(score.to_dict())
                row["score_complete"] = True
                row["score_source"] = score_sources.get(record.song_id, "manual")
            rows.append(row)
        write_csv_rows(path, rows)
