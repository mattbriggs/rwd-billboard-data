"""Unit tests for normalization and lyric feature rules."""

from __future__ import annotations

from study_system.domain.feature_rules import (
    ascii_punctuation_fold,
    artist_match,
    collect_names_from_genre_objects,
    extract_relation_artists,
    first_year_from_text,
    lyrics_candidate_pairs,
    lyric_features,
    normalize_text,
    parse_artist_credit,
    relation_flags,
    safe_int,
    strip_title_suffixes,
    title_match,
    title_similarity,
)


def test_normalize_text_strips_featuring_and_punctuation() -> None:
    assert normalize_text("Jonas Blue ft. Dakota!") == "jonas blue"
    assert ascii_punctuation_fold("You’ve Lost That Lovin’ Feelin’") == "You've Lost That Lovin' Feelin'"
    assert strip_title_suffixes("Pick Up The Pieces - Remastered 2011") == "Pick Up The Pieces"


def test_title_similarity_handles_parenthetical_variants() -> None:
    assert title_similarity("Fast Car", "Fast Car (Live)") >= 0.95


def test_lyric_features_extract_expected_counts() -> None:
    features = lyric_features("Fast Car", "Fast car\nFast car\nDo you know?\nI know you do.")
    assert features.word_count == 11
    assert features.line_count == 4
    assert features.title_repetition_count == 2
    assert features.question_count == 1
    assert features.pronoun_counts["first_person"] == 1
    assert features.pronoun_counts["second_person"] == 2


def test_matching_helpers_cover_provider_cases() -> None:
    artist_credit = [{"name": "Tracy Chapman", "joinphrase": " & "}, {"name": "Guest"}]
    assert parse_artist_credit(artist_credit) == "Tracy Chapman & Guest"
    assert safe_int("7") == 7
    assert first_year_from_text("1988-04-06") == 1988
    assert collect_names_from_genre_objects([{"name": "folk", "count": 2}, {"name": "rock", "count": 1}]) == [
        "folk",
        "rock",
    ]
    relations = [{"type": "writer", "artist": {"name": "Tracy Chapman"}}]
    assert extract_relation_artists(relations, matching_types={"writer"}) == ["Tracy Chapman"]
    assert relation_flags([{"type": "samples material"}])["has_sample"] is True
    assert artist_match("Jonas Blue", "Jonas Blue Featuring Dakota") is True
    assert title_match("Fast Car", "Fast Car (Live)") is True
    pairs = lyrics_candidate_pairs("Fast Car", "Tracy Chapman feat. Guest", "Fast Car", "Tracy Chapman")
    assert ("Fast Car", "Tracy Chapman") in pairs
    awb_pairs = lyrics_candidate_pairs(
        "Pick Up The Pieces (Album Version)",
        "AWB",
        "Pick Up The Pieces (Album Version)",
        "AWB",
    )
    assert ("Pick Up The Pieces", "Average White Band") in awb_pairs
    unicode_pairs = lyrics_candidate_pairs(
        "You’ve Lost That Lovin’ Feelin’",
        "Olivia Newton‐John",
        None,
        None,
    )
    assert ("You've Lost That Lovin' Feelin'", "Olivia Newton-John") in unicode_pairs
