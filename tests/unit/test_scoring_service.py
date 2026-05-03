"""Unit tests for blind scoring workflows."""

from __future__ import annotations

from study_system.application.services.scoring_service import ScoringService
from study_system.domain.models import LyricAsset, LyricFeatureSet, ScoreCard, SongRecord


def _record() -> SongRecord:
    return SongRecord(
        song_id="song-1",
        query_title="Fast Car",
        query_artist="Tracy Chapman",
        title="Fast Car",
        artist="Tracy Chapman",
        year=1988,
        chart_rank=6,
        source_chart_list="Billboard Hot 100 weekly archive",
        genre=[],
        songwriters=[],
        producers=[],
        label=[],
        writer_count=None,
        producer_count=None,
        is_cover=False,
        has_sample=False,
        lyrics_source_url="https://example.com",
        lyrics_found=True,
        recording_length_ms=None,
        first_release_date=None,
        billboard_best_chart_week="1988-08-27",
        billboard_weeks_on_chart_max=22,
        lyric_asset=LyricAsset(
            found=True,
            source="lyrics.ovh",
            source_url="https://example.com",
            lyrics="Fast car\nFast car",
        ),
        lyric_features=LyricFeatureSet(
            text_length_chars=18,
            word_count=80,
            unique_word_ratio=0.42,
            line_count=16,
            stanza_count=4,
            repeated_line_ratio=0.25,
            title_repetition_count=3,
            question_count=1,
            pronoun_counts={"first_person": 5, "second_person": 4, "third_person": 2},
            proper_noun_count_heuristic=1,
            proper_nouns_heuristic=["Fast"],
        ),
    )


def test_export_blind_packets_hides_artist_and_year() -> None:
    packets = ScoringService().export_blind_packets([_record()], include_lyrics=False)
    packet = packets[0]
    assert "artist" not in packet
    assert "year" not in packet
    assert "lyrics_text" not in packet
    assert packet["speaker_situation_clarity"] is None
    assert packet["context_independence"] is None
    assert packet["scorer_id"] is None


def test_export_score_packets_defaults_to_full_context_and_lyrics() -> None:
    packets = ScoringService().export_score_packets([_record()])
    packet = packets[0]
    assert packet["artist"] == "Tracy Chapman"
    assert packet["lyrics_text"] == "Fast car\nFast car"
    assert packet["packet_mode"] == "full_context"
    assert packet["speaker_situation_clarity"] is None


def test_complete_scores_generates_fallback_scores_for_lyric_records() -> None:
    scores, score_sources, auto_scored_song_ids = ScoringService().complete_scores([_record()], [])
    assert len(scores) == 1
    assert scores[0].scorer_id == "auto_heuristic"
    assert score_sources[_record().song_id] == "auto_heuristic"
    assert auto_scored_song_ids == [_record().song_id]


def test_summarize_scores_returns_mean_sci() -> None:
    scores = [
        ScoreCard("song-1", 2, 2, 1, 2, 1, scorer_id="a"),
        ScoreCard("song-1", 1, 1, 1, 1, 1, scorer_id="b"),
    ]
    summary = ScoringService().summarize_scores(scores)
    assert summary[0]["mean_sci"] == 6.5
