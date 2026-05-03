"""Unit tests for the CLI and command wrappers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from study_system.domain.models import ScoreCard
from study_system.infrastructure.persistence.repositories import JsonScoreRepository, JsonSongRepository
from study_system.interfaces import cli
from study_system.interfaces.cli import main
from study_system.interfaces.commands.lookup import run_lookup
from tests.unit.test_chart_source import FIXTURE
from tests.unit.test_scoring_service import _record


class FakeLookupService:
    def lookup_song(self, request):
        return _record()


def test_run_lookup_returns_serializable_payload() -> None:
    payload = run_lookup(
        FakeLookupService(),
        title="Fast Car",
        artist="Tracy Chapman",
        billboard_file=FIXTURE,
        include_lyrics=False,
    )
    assert payload["title"] == "Fast Car"


def test_cli_build_corpus_creates_output(tmp_path: Path) -> None:
    output = tmp_path / "corpus.json"
    exit_code = main(
        [
            "build-corpus",
            "--years",
            "1988",
            "--top-n",
            "2",
            "--billboard-file",
            str(FIXTURE),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload[0]["title"] == "Roll With It"


def test_cli_score_packets_and_export_dataset(tmp_path: Path) -> None:
    record = _record()
    records_path = tmp_path / "records.json"
    JsonSongRepository().save_records(records_path, [record], include_lyrics=True)

    packets_path = tmp_path / "packets.json"
    assert main(["score-packets", "--records-file", str(records_path), "--output", str(packets_path)]) == 0
    packets = json.loads(packets_path.read_text(encoding="utf-8"))
    assert packets[0]["artist"] == "Tracy Chapman"
    assert packets[0]["lyrics_text"] == "Fast car\nFast car"
    assert packets[0]["speaker_situation_clarity"] is None

    scores_path = tmp_path / "scores.json"
    JsonScoreRepository().save_scores(scores_path, [ScoreCard(record.song_id, 2, 2, 1, 2, 1, scorer_id="cli")])

    final_path = tmp_path / "final.csv"
    assert main(
        [
            "export-dataset",
            "--records-file",
            str(records_path),
            "--scores-file",
            str(scores_path),
            "--output",
            str(final_path),
        ]
    ) == 0
    assert "self_containment_index" in final_path.read_text(encoding="utf-8")


def test_cli_score_packets_blind_mode_strips_context(tmp_path: Path) -> None:
    record = _record()
    records_path = tmp_path / "records.json"
    JsonSongRepository().save_records(records_path, [record], include_lyrics=True)

    packets_path = tmp_path / "blind-packets.json"
    assert main(
        [
            "score-packets",
            "--records-file",
            str(records_path),
            "--output",
            str(packets_path),
            "--blind",
            "--omit-lyrics",
        ]
    ) == 0
    packets = json.loads(packets_path.read_text(encoding="utf-8"))
    assert "artist" not in packets[0]
    assert "lyrics_text" not in packets[0]


@pytest.mark.parametrize(
    ("extra_args", "expected_lyrics_text"),
    [
        ([], "Fast car\nFast car"),
        (["--omit-lyrics"], None),
    ],
)
def test_cli_enrich_defaults_to_persisting_lyrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_args: list[str],
    expected_lyrics_text: str | None,
) -> None:
    class FakeEnrichmentService:
        def enrich_corpus(self, entries, include_lyrics: bool, billboard_file: Path):
            return [_record()]

    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(
        json.dumps([{"year": 1988, "title": "Fast Car", "artist": "Tracy Chapman"}]),
        encoding="utf-8",
    )
    output_path = tmp_path / "records.json"

    monkeypatch.setattr(cli, "_build_enrichment_service", lambda billboard_file: FakeEnrichmentService())

    exit_code = main(
        [
            "enrich",
            "--corpus-file",
            str(corpus_path),
            "--billboard-file",
            str(FIXTURE),
            "--output",
            str(output_path),
            *extra_args,
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["lyrics_text"] == expected_lyrics_text
    assert payload[0]["lyric_asset"]["lyrics"] is None


def test_cli_export_dataset_skips_unfilled_score_packets_by_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    record = _record()
    records_path = tmp_path / "records.json"
    JsonSongRepository().save_records(records_path, [record], include_lyrics=True)

    scores_path = tmp_path / "scores.json"
    scores_path.write_text(
        json.dumps(
            [
                {
                    "song_id": record.song_id,
                    "title": record.title,
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
                }
            ]
        ),
        encoding="utf-8",
    )

    output_path = tmp_path / "final.csv"
    assert (
        main(
            [
                "export-dataset",
                "--records-file",
                str(records_path),
                "--scores-file",
                str(scores_path),
                "--output",
                str(output_path),
            ]
    )
        == 0
    )
    stderr = capsys.readouterr().err
    assert "Skipped 1 incomplete scoring packet" in stderr
    assert "Generated fallback heuristic scores for 1 lyric-bearing song" in stderr
    text = output_path.read_text(encoding="utf-8")
    assert "score_complete" in text
    assert "auto_heuristic" in text


def test_cli_export_dataset_strict_scores_rejects_unfilled_packets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    record = _record()
    records_path = tmp_path / "records.json"
    JsonSongRepository().save_records(records_path, [record], include_lyrics=True)

    scores_path = tmp_path / "scores.json"
    scores_path.write_text(
        json.dumps(
            [
                {
                    "song_id": record.song_id,
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
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "export-dataset",
                "--records-file",
                str(records_path),
                "--scores-file",
                str(scores_path),
                "--output",
                str(tmp_path / "final.csv"),
                "--strict-scores",
            ]
        )

    assert exc_info.value.code == 2
    stderr = capsys.readouterr().err
    assert "unfilled scoring packet" in stderr
