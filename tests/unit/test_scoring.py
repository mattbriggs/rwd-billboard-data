"""Unit tests for scoring rules."""

from __future__ import annotations

import pytest

from study_system.domain.models import ScoreCard
from study_system.domain.scoring import calculate_sci, validate_score_card


def test_calculate_sci_returns_total() -> None:
    score = ScoreCard(
        song_id="song-1",
        speaker_situation_clarity=2,
        thematic_unity=2,
        image_motif_integration=1,
        structural_development=2,
        context_independence=1,
    )
    assert calculate_sci(score) == 8


def test_validate_score_card_rejects_invalid_subscore() -> None:
    score = ScoreCard(
        song_id="song-1",
        speaker_situation_clarity=3,
        thematic_unity=2,
        image_motif_integration=1,
        structural_development=2,
        context_independence=1,
    )
    with pytest.raises(ValueError):
        validate_score_card(score)
