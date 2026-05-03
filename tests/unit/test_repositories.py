"""Unit tests for JSON repositories."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from study_system.domain.models import ScoreCard
from study_system.infrastructure.persistence.repositories import InvalidScoreFileError, JsonScoreRepository, JsonSongRepository
from tests.unit.test_scoring_service import _record


def test_score_repository_round_trip(tmp_path: Path) -> None:
    repo = JsonScoreRepository()
    path = tmp_path / "scores.json"
    scores = [ScoreCard(_record().song_id, 2, 2, 1, 2, 1, scorer_id="tester")]
    repo.save_scores(path, scores)
    loaded = repo.load_scores(path)
    assert loaded[0].self_containment_index == 8


def test_song_repository_round_trip_preserves_top_level_lyrics_text(tmp_path: Path) -> None:
    repo = JsonSongRepository()
    path = tmp_path / "records.json"
    record = _record()

    repo.save_records(path, [record], include_lyrics=True)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload[0]["lyrics_text"] == record.lyrics_text
    assert payload[0]["lyric_asset"]["lyrics"] is None

    loaded = repo.load_records(path)
    assert loaded[0].lyrics_text == record.lyrics_text


def test_score_repository_rejects_unfilled_scoring_packets(tmp_path: Path) -> None:
    repo = JsonScoreRepository()
    path = tmp_path / "scores.json"
    path.write_text(
        json.dumps(
            [
                {
                    "song_id": "song-1",
                    "title": "Fast Car",
                    "score_fields": [
                        "speaker_situation_clarity",
                        "thematic_unity",
                        "image_motif_integration",
                        "structural_development",
                        "context_independence",
                    ],
                    "speaker_situation_clarity": None,
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(InvalidScoreFileError, match="unfilled scoring packet"):
        repo.load_scores(path)


def test_score_repository_can_skip_unfilled_scoring_packets(tmp_path: Path) -> None:
    repo = JsonScoreRepository()
    path = tmp_path / "scores.json"
    path.write_text(
        json.dumps(
            [
                {
                    "song_id": "song-1",
                    "score_fields": [
                        "speaker_situation_clarity",
                        "thematic_unity",
                        "image_motif_integration",
                        "structural_development",
                        "context_independence",
                    ],
                    "speaker_situation_clarity": None,
                    "thematic_unity": None,
                    "image_motif_integration": None,
                    "structural_development": None,
                    "context_independence": None,
                },
                ScoreCard(_record().song_id, 2, 2, 1, 2, 1, scorer_id="tester").to_dict(),
            ]
        ),
        encoding="utf-8",
    )

    scores, skipped_song_ids = repo.load_scores_with_report(path, skip_incomplete=True)

    assert len(scores) == 1
    assert skipped_song_ids == ["song-1"]
