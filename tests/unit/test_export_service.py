"""Unit tests for export workflows."""

from __future__ import annotations

import json
from pathlib import Path

from study_system.application.services.export_service import ExportService
from study_system.domain.models import ScoreCard
from tests.unit.test_scoring_service import _record


def test_export_json_writes_payload(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    ExportService().export_json(path, {"ok": True})
    assert json.loads(path.read_text(encoding="utf-8"))["ok"] is True


def test_export_final_dataset_writes_score_fields(tmp_path: Path) -> None:
    path = tmp_path / "final.csv"
    record = _record()
    score = ScoreCard(record.song_id, 2, 2, 1, 2, 1, scorer_id="tester")
    ExportService().export_final_dataset(path, [record], [score], score_sources={record.song_id: "manual"})
    text = path.read_text(encoding="utf-8")
    assert "self_containment_index" in text
    assert record.song_id in text
    assert "lyrics_text" in text
    assert "Fast car" in text
    assert "score_complete" in text
    assert "score_source" in text
    assert "manual" in text
    assert "query_title" in text
    assert "source_chart_list" in text


def test_export_final_dataset_keeps_blank_score_columns_without_scores(tmp_path: Path) -> None:
    path = tmp_path / "final.csv"
    record = _record()
    ExportService().export_final_dataset(path, [record], [])
    text = path.read_text(encoding="utf-8")
    assert "speaker_situation_clarity" in text
    assert "score_complete" in text
    assert "False" in text
    assert "missing" in text


def test_export_flat_records_csv_writes_lyrics_text_column(tmp_path: Path) -> None:
    path = tmp_path / "records.csv"
    record = _record()
    ExportService().export_flat_records_csv(path, [record])
    text = path.read_text(encoding="utf-8")
    assert "lyrics_text" in text
    assert "Fast car" in text
