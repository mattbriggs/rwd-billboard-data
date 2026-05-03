"""Filesystem repositories for song records and score cards."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from study_system.domain.models import ChartSummary, LyricAsset, LyricFeatureSet, MetadataSummary, ProvenanceEntry, ScoreCard, SongRecord
from study_system.domain.scoring import SCORE_FIELD_NAMES, validate_score_card
from study_system.infrastructure.persistence.file_store import read_json, write_json


class InvalidScoreFileError(ValueError):
    """Raised when a score JSON file is not in the expected completed-score format."""


class JsonSongRepository:
    """Persist song records as JSON arrays."""

    def save_records(self, path: Path, records: list[SongRecord], include_lyrics: bool = True) -> None:
        """Save song records to a JSON file."""

        write_json(path, [record.to_dict(include_lyrics=include_lyrics) for record in records], pretty=True)

    def load_records(self, path: Path) -> list[SongRecord]:
        """Load song records from a JSON file."""

        payload = read_json(path)
        records: list[SongRecord] = []
        for item in payload:
            lyric_features = item.get("lyric_features")
            lyric_asset = item.get("lyric_asset")
            lyrics_text = item.get("lyrics_text")
            metadata_summary = item.get("metadata_summary")
            chart_summary = item.get("chart_summary")
            provenance = [ProvenanceEntry(**entry) for entry in item.get("provenance", [])]
            if lyric_asset:
                lyric_asset_payload = dict(lyric_asset)
                lyric_asset_payload["lyrics"] = lyrics_text or lyric_asset_payload.get("lyrics")
                lyric_asset_instance = LyricAsset(**lyric_asset_payload)
            elif lyrics_text:
                lyric_asset_instance = LyricAsset(
                    found=item.get("lyrics_found", True),
                    source="stored",
                    source_url=item.get("lyrics_source_url"),
                    lyrics=lyrics_text,
                )
            else:
                lyric_asset_instance = None
            records.append(
                SongRecord(
                    song_id=item["song_id"],
                    query_title=item["query_title"],
                    query_artist=item["query_artist"],
                    title=item["title"],
                    artist=item["artist"],
                    year=item.get("year"),
                    chart_rank=item.get("chart_rank"),
                    source_chart_list=item["source_chart_list"],
                    genre=item.get("genre", []),
                    songwriters=item.get("songwriters", []),
                    producers=item.get("producers", []),
                    label=item.get("label", []),
                    writer_count=item.get("writer_count"),
                    producer_count=item.get("producer_count"),
                    is_cover=item.get("is_cover"),
                    has_sample=item.get("has_sample"),
                    lyrics_source_url=item.get("lyrics_source_url"),
                    lyrics_found=item.get("lyrics_found", False),
                    recording_length_ms=item.get("recording_length_ms"),
                    first_release_date=item.get("first_release_date"),
                    billboard_best_chart_week=item.get("billboard_best_chart_week"),
                    billboard_weeks_on_chart_max=item.get("billboard_weeks_on_chart_max"),
                    lyric_features=LyricFeatureSet(**lyric_features) if lyric_features else None,
                    lyric_asset=lyric_asset_instance,
                    metadata_summary=MetadataSummary(**metadata_summary) if metadata_summary else None,
                    chart_summary=ChartSummary(**chart_summary) if chart_summary else None,
                    provenance=provenance,
                    errors=item.get("errors", []),
                )
            )
        return records


class JsonScoreRepository:
    """Persist score cards as JSON arrays."""

    def save_scores(self, path: Path, scores: list[ScoreCard]) -> None:
        """Save score cards to JSON."""

        write_json(path, [score.to_dict() for score in scores], pretty=True)

    def load_scores(self, path: Path) -> list[ScoreCard]:
        """Load score cards from JSON."""

        scores, _ = self.load_scores_with_report(path, skip_incomplete=False)
        return scores

    def load_scores_with_report(self, path: Path, *, skip_incomplete: bool = False) -> tuple[list[ScoreCard], list[str]]:
        """Load score cards and optionally skip incomplete scoring packets.

        :param path: Input JSON path.
        :param skip_incomplete: Skip unfilled scoring packets instead of raising.
        :returns: Loaded score cards and skipped song identifiers.
        """

        payload = read_json(path)
        if not isinstance(payload, list):
            raise InvalidScoreFileError(
                f"Scores file '{path}' must contain a JSON array of completed score objects."
            )

        scores: list[ScoreCard] = []
        skipped_song_ids: list[str] = []
        for index, item in enumerate(payload):
            if skip_incomplete and isinstance(item, dict) and self._is_incomplete_packet(item):
                skipped_song_ids.append(str(item.get("song_id", f"item-{index}")))
                continue
            scores.append(self._build_score_card(path, item, index))
        return scores, skipped_song_ids

    def _build_score_card(self, path: Path, item: object, index: int) -> ScoreCard:
        """Build a validated score card from one JSON item."""

        if not isinstance(item, dict):
            raise InvalidScoreFileError(
                f"Scores file '{path}' item {index} must be a JSON object, not {type(item).__name__}."
            )

        song_id = str(item.get("song_id", f"item-{index}"))
        missing_fields = [field for field in SCORE_FIELD_NAMES if self._is_missing_value(item.get(field))]
        if missing_fields:
            if "score_fields" in item:
                raise InvalidScoreFileError(
                    f"Scores file '{path}' contains an unfilled scoring packet for song_id '{song_id}'. "
                    f"Fill in {', '.join(SCORE_FIELD_NAMES)} with integers from 0 to 2 before running "
                    f"'export-dataset'."
                )
            raise InvalidScoreFileError(
                f"Scores file '{path}' item {index} for song_id '{song_id}' is missing required score "
                f"field(s): {', '.join(missing_fields)}."
            )

        score_card = ScoreCard(
            song_id=song_id,
            speaker_situation_clarity=self._coerce_subscore(
                path, song_id, "speaker_situation_clarity", item["speaker_situation_clarity"]
            ),
            thematic_unity=self._coerce_subscore(path, song_id, "thematic_unity", item["thematic_unity"]),
            image_motif_integration=self._coerce_subscore(
                path, song_id, "image_motif_integration", item["image_motif_integration"]
            ),
            structural_development=self._coerce_subscore(
                path, song_id, "structural_development", item["structural_development"]
            ),
            context_independence=self._coerce_subscore(
                path, song_id, "context_independence", item["context_independence"]
            ),
            scorer_id=str(item.get("scorer_id", "unknown") or "unknown"),
            notes=None if item.get("notes") is None else str(item.get("notes")),
        )
        try:
            validate_score_card(score_card)
        except ValueError as exc:
            raise InvalidScoreFileError(
                f"Scores file '{path}' has an out-of-range value for song_id '{song_id}'. "
                f"Each rubric score must be an integer from 0 to 2."
            ) from exc
        return score_card

    def _coerce_subscore(self, path: Path, song_id: str, field_name: str, value: object) -> int:
        """Coerce one rubric subscore to an integer."""

        if isinstance(value, bool):
            raise InvalidScoreFileError(
                f"Scores file '{path}' has an invalid boolean for '{field_name}' on song_id '{song_id}'. "
                f"Use integers from 0 to 2."
            )
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
        raise InvalidScoreFileError(
            f"Scores file '{path}' has a non-integer value for '{field_name}' on song_id '{song_id}'. "
            f"Use integers from 0 to 2."
        )

    def _is_incomplete_packet(self, item: dict[object, object]) -> bool:
        """Return whether one score item is an unfilled scoring packet."""

        return "score_fields" in item and any(self._is_missing_value(item.get(field)) for field in SCORE_FIELD_NAMES)

    def _is_missing_value(self, value: object) -> bool:
        """Return whether a score value should be treated as missing."""

        return value is None or (isinstance(value, str) and not value.strip())
