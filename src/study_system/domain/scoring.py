"""Scoring rules for the Self-Containment Index."""

from __future__ import annotations

from study_system.domain.models import ScoreCard, SongRecord

SCORE_FIELD_NAMES = (
    "speaker_situation_clarity",
    "thematic_unity",
    "image_motif_integration",
    "structural_development",
    "context_independence",
)


def validate_subscore(value: int) -> None:
    """Validate a rubric subscore.

    :param value: Score from 0 to 2 inclusive.
    :raises ValueError: If the score is outside the permitted range.
    """

    if value < 0 or value > 2:
        raise ValueError("Subscores must be between 0 and 2 inclusive.")


def validate_score_card(score_card: ScoreCard) -> None:
    """Validate all score card subscores.

    :param score_card: Score card to validate.
    """

    validate_subscore(score_card.speaker_situation_clarity)
    validate_subscore(score_card.thematic_unity)
    validate_subscore(score_card.image_motif_integration)
    validate_subscore(score_card.structural_development)
    validate_subscore(score_card.context_independence)


def calculate_sci(score_card: ScoreCard) -> int:
    """Calculate the Self-Containment Index after validation.

    :param score_card: Score card to validate and total.
    :returns: Aggregate score from 0 to 10.
    """

    validate_score_card(score_card)
    return score_card.self_containment_index


def heuristic_score_record(record: SongRecord, scorer_id: str = "auto_heuristic") -> ScoreCard | None:
    """Create a deterministic fallback score from lyric features.

    :param record: Enriched song record.
    :param scorer_id: Identifier for the fallback scorer.
    :returns: Fallback score card or ``None`` when lyric features are unavailable.
    """

    if record.lyric_features is None:
        return None

    features = record.lyric_features
    pronoun_counts = features.pronoun_counts
    first_person = pronoun_counts.get("first_person", 0)
    second_person = pronoun_counts.get("second_person", 0)
    third_person = pronoun_counts.get("third_person", 0)
    total_pronouns = first_person + second_person + third_person
    word_count = max(features.word_count, 1)
    pronoun_density = total_pronouns / word_count
    repeated_line_ratio = features.repeated_line_ratio or 0.0
    unique_word_ratio = features.unique_word_ratio or 0.0

    score_card = ScoreCard(
        song_id=record.song_id,
        speaker_situation_clarity=_speaker_situation_clarity(
            pronoun_density,
            total_pronouns,
            first_person + second_person,
            features.question_count,
        ),
        thematic_unity=_thematic_unity(features.title_repetition_count, repeated_line_ratio),
        image_motif_integration=_image_motif_integration(
            unique_word_ratio,
            features.proper_noun_count_heuristic,
            features.word_count,
        ),
        structural_development=_structural_development(features.stanza_count, features.line_count),
        context_independence=_context_independence(
            features.word_count,
            features.title_repetition_count,
            total_pronouns,
        ),
        scorer_id=scorer_id,
        notes="Fallback heuristic score generated from lyric features.",
    )
    validate_score_card(score_card)
    return score_card


def _speaker_situation_clarity(
    pronoun_density: float,
    total_pronouns: int,
    first_or_second_person: int,
    question_count: int,
) -> int:
    """Approximate speaker and addressee clarity from pronoun usage."""

    if pronoun_density >= 0.12 or first_or_second_person >= 8 or total_pronouns >= 12:
        return 2
    if pronoun_density >= 0.05 or total_pronouns >= 4 or question_count >= 1:
        return 1
    return 0


def _thematic_unity(title_repetition_count: int, repeated_line_ratio: float) -> int:
    """Approximate thematic unity from refrain and title recurrence."""

    if title_repetition_count >= 3 or repeated_line_ratio >= 0.25:
        return 2
    if title_repetition_count >= 1 or repeated_line_ratio >= 0.1:
        return 1
    return 0


def _image_motif_integration(unique_word_ratio: float, proper_noun_count: int, word_count: int) -> int:
    """Approximate motif integration from lexical variety and named details."""

    if proper_noun_count >= 2 or (unique_word_ratio >= 0.4 and word_count >= 80):
        return 2
    if proper_noun_count >= 1 or unique_word_ratio >= 0.28:
        return 1
    return 0


def _structural_development(stanza_count: int, line_count: int) -> int:
    """Approximate development from stanza count and overall shape."""

    if stanza_count >= 3 and line_count >= 14:
        return 2
    if stanza_count >= 2 or line_count >= 10:
        return 1
    return 0


def _context_independence(word_count: int, title_repetition_count: int, total_pronouns: int) -> int:
    """Approximate context independence from lyric sufficiency signals."""

    if word_count >= 80 and (title_repetition_count >= 1 or total_pronouns >= 8):
        return 2
    if word_count >= 40:
        return 1
    return 0
