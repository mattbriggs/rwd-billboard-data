"""Normalization, matching, and lyric feature extraction rules."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Iterable

from study_system.domain.models import LyricFeatureSet

FIRST_PERSON_PRONOUNS = {
    "i",
    "me",
    "my",
    "mine",
    "myself",
    "we",
    "us",
    "our",
    "ours",
    "ourselves",
}
SECOND_PERSON_PRONOUNS = {"you", "your", "yours", "yourself", "yourselves", "u"}
THIRD_PERSON_PRONOUNS = {
    "he",
    "him",
    "his",
    "himself",
    "she",
    "her",
    "hers",
    "herself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "it",
    "its",
    "itself",
}
PROPER_NOUN_STOPWORDS = {
    "I",
    "I'm",
    "I've",
    "I'll",
    "I'd",
    "A",
    "An",
    "And",
    "But",
    "For",
    "If",
    "In",
    "Is",
    "It",
    "No",
    "Not",
    "Of",
    "Oh",
    "So",
    "The",
    "This",
    "To",
    "We",
    "You",
}
ARTIST_ALIAS_MAP = {
    "awb": ["Average White Band"],
    "elo": ["Electric Light Orchestra"],
    "csn": ["Crosby, Stills & Nash"],
    "csny": ["Crosby, Stills, Nash & Young"],
}
TITLE_SUFFIX_PATTERNS = (
    r"\s*-\s*(mono|stereo)\s*$",
    r"\s*-\s*(radio edit|single edit|album version|single version|lp version)\s*$",
    r"\s*-\s*(edit|mix|version)\s*$",
    r"\s*-\s*(live|live at .+)\s*$",
    r"\s*-\s*(remaster|remastered)(?:\s+\d{4})?\s*$",
)


def normalize_text(value: str) -> str:
    """Normalize arbitrary text for fuzzy matching.

    :param value: Source string.
    :returns: Lower-cased, accent-stripped normalized string.
    """

    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\b(feat|featuring|ft)\.?\b.*$", "", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def ascii_punctuation_fold(value: str) -> str:
    """Normalize punctuation variants to provider-friendly ASCII forms.

    :param value: Source string.
    :returns: Text with normalized apostrophes, quotes, dashes, and spaces.
    """

    table = str.maketrans(
        {
            "’": "'",
            "‘": "'",
            "´": "'",
            "`": "'",
            "“": '"',
            "”": '"',
            "–": "-",
            "—": "-",
            "‐": "-",
            "\u00a0": " ",
        }
    )
    return value.translate(table)


def normalize_title_for_matching(value: str) -> str:
    """Normalize title text and strip bracketed qualifiers.

    :param value: Title string.
    :returns: Match-oriented normalized title.
    """

    value = re.sub(r"\s*\[[^\]]+\]", "", value)
    value = re.sub(r"\s*\([^)]*\)", "", value)
    return normalize_text(value)


def strip_title_suffixes(value: str) -> str:
    """Strip common non-lyric title descriptors from the end of a title.

    :param value: Title string.
    :returns: Simplified title variant.
    """

    result = ascii_punctuation_fold(value).strip()
    for pattern in TITLE_SUFFIX_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
    return result


def normalize_line(value: str) -> str:
    """Normalize a lyric line for repeat counting.

    :param value: Lyric line.
    :returns: Normalized line.
    """

    return re.sub(r"\s+", " ", normalize_text(value)).strip()


def similarity(a: str, b: str) -> float:
    """Calculate normalized similarity between two strings.

    :param a: First string.
    :param b: Second string.
    :returns: Ratio from 0.0 to 1.0.
    """

    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def title_similarity(a: str, b: str) -> float:
    """Calculate title similarity after title-specific normalization.

    :param a: First title.
    :param b: Second title.
    :returns: Ratio from 0.0 to 1.0.
    """

    a_norm = normalize_title_for_matching(a)
    b_norm = normalize_title_for_matching(b)
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    if a_norm in b_norm or b_norm in a_norm:
        return 0.95
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """Deduplicate a list while preserving original order.

    :param values: Candidate values.
    :returns: Deduplicated list.
    """

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        key = normalize_text(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def safe_int(value: Any) -> int | None:
    """Convert a value to ``int`` when possible.

    :param value: Raw value.
    :returns: Converted integer or ``None``.
    """

    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def first_year_from_text(value: str | None) -> int | None:
    """Extract the first 4-digit year from text.

    :param value: Source text.
    :returns: Parsed year or ``None``.
    """

    if not value:
        return None
    match = re.search(r"\b(\d{4})\b", value)
    return int(match.group(1)) if match else None


def parse_artist_credit(artist_credit: list[Any] | None) -> str:
    """Join MusicBrainz artist-credit payloads into a single string.

    :param artist_credit: MusicBrainz artist-credit payload.
    :returns: Joined artist credit.
    """

    if not artist_credit:
        return ""
    parts: list[str] = []
    for item in artist_credit:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name:
            parts.append(name)
        joinphrase = item.get("joinphrase")
        if joinphrase:
            parts.append(joinphrase)
    return "".join(parts).strip()


def collect_names_from_genre_objects(items: list[dict[str, Any]] | None) -> list[str]:
    """Extract ranked names from MusicBrainz genre or tag payloads.

    :param items: Provider payload.
    :returns: Ranked names.
    """

    if not items:
        return []
    ranked = sorted(
        (item for item in items if item.get("name")),
        key=lambda item: (-(safe_int(item.get("count") or 0) or 0), item.get("name")),
    )
    return dedupe_preserve_order([item["name"] for item in ranked])


def extract_relation_artists(
    relations: list[dict[str, Any]] | None,
    matching_types: set[str] | None = None,
    contains_any: tuple[str, ...] = (),
) -> list[str]:
    """Extract artist names from provider relation payloads.

    :param relations: Relation payloads.
    :param matching_types: Exact relation types to include.
    :param contains_any: Fragments that relation type must contain.
    :returns: Deduplicated artist names.
    """

    artists: list[str] = []
    for relation in relations or []:
        relation_type = str(relation.get("type") or "").lower()
        if matching_types and relation_type not in matching_types:
            continue
        if contains_any and not any(fragment in relation_type for fragment in contains_any):
            continue
        artist = relation.get("artist") or {}
        name = artist.get("name")
        if name:
            artists.append(name)
    return dedupe_preserve_order(artists)


def relation_flags(relations: list[dict[str, Any]] | None) -> dict[str, bool]:
    """Derive cover and sample flags from provider relations.

    :param relations: Relation payloads.
    :returns: Dictionary containing ``is_cover`` and ``has_sample``.
    """

    is_cover = False
    has_sample = False
    for relation in relations or []:
        relation_type = str(relation.get("type") or "").lower()
        attributes = [str(item).lower() for item in relation.get("attributes") or []]
        haystack = " ".join([relation_type, *attributes])
        if "cover" in haystack:
            is_cover = True
        if "sample" in haystack or "interpolat" in haystack:
            has_sample = True
    return {"is_cover": is_cover, "has_sample": has_sample}


def lyrics_candidate_pairs(
    title: str, artist: str, matched_title: str | None, matched_artist: str | None
) -> list[tuple[str, str]]:
    """Generate title and artist variants for lyric provider lookup.

    :param title: Original title.
    :param artist: Original artist.
    :param matched_title: Canonical title variant.
    :param matched_artist: Canonical artist variant.
    :returns: Ordered lookup candidates.
    """

    title_variants = [item for item in [matched_title, title] if item]
    titles = _ordered_unique_variants(_title_lookup_variants(current_title) for current_title in title_variants)

    artist_variants = [item for item in [matched_artist, artist] if item]
    artists = _ordered_unique_variants(_artist_lookup_variants(current_artist) for current_artist in artist_variants)

    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for candidate_artist in artists:
        for candidate_title in titles:
            key = (normalize_text(candidate_artist), normalize_title_for_matching(candidate_title))
            if not all(key) or key in seen:
                continue
            seen.add(key)
            pairs.append((candidate_title, candidate_artist))
    return pairs


def _ordered_unique_variants(variant_groups: Iterable[list[str]]) -> list[str]:
    """Flatten nested variant groups while preserving order and uniqueness."""

    values: list[str] = []
    seen: set[str] = set()
    for group in variant_groups:
        for value in group:
            normalized = re.sub(r"\s+", " ", value).strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            values.append(normalized)
    return values


def _title_lookup_variants(value: str) -> list[str]:
    """Build provider lookup variants for a song title."""

    variants: list[str] = []
    current = ascii_punctuation_fold(value).strip()
    stripped = re.sub(r"\s*\([^)]*\)", "", current).strip()
    stripped = re.sub(r"\s*\[[^\]]+\]", "", stripped).strip()
    suffix_stripped = strip_title_suffixes(stripped)

    base_variants = [suffix_stripped, stripped, current, value]
    for item in base_variants:
        if not item:
            continue
        variants.append(item)
        no_quotes = item.replace('"', "").replace("'", "")
        variants.append(no_quotes)
    return variants


def _artist_lookup_variants(value: str) -> list[str]:
    """Build provider lookup variants for an artist name."""

    variants: list[str] = []
    current = ascii_punctuation_fold(value).strip()
    stripped = re.split(r"\b(?:feat|featuring|ft)\.?\b", current, flags=re.IGNORECASE)[0].strip()

    for item in [stripped, current, value]:
        if not item:
            continue
        variants.append(item)
        variants.append(item.replace("&", "and"))
        variants.append(item.replace(" and ", " & "))
        if item.lower().startswith("the "):
            variants.append(item[4:])

    alias_key = normalize_text(stripped)
    for alias in ARTIST_ALIAS_MAP.get(alias_key, []):
        variants.append(alias)

    return variants


def count_title_mentions(title: str, lyrics: str) -> int:
    """Count occurrences of the normalized title in lyric text.

    :param title: Song title.
    :param lyrics: Lyric text.
    :returns: Number of title occurrences.
    """

    title_norm = normalize_title_for_matching(title)
    lyrics_norm = normalize_text(lyrics)
    if not title_norm or not lyrics_norm:
        return 0
    pattern = re.compile(rf"(?<!\w){re.escape(title_norm)}(?!\w)")
    return len(pattern.findall(lyrics_norm))


def proper_noun_stats(lines: list[str]) -> tuple[int, list[str]]:
    """Compute heuristic proper noun statistics for lyric lines.

    :param lines: Non-empty lyric lines.
    :returns: Count and sample of proper noun tokens.
    """

    values: list[str] = []
    token_pattern = re.compile(r"[A-Za-z][A-Za-z'’-]*")
    for line in lines:
        tokens = token_pattern.findall(line)
        for index, token in enumerate(tokens):
            if index == 0:
                continue
            if token in PROPER_NOUN_STOPWORDS:
                continue
            if token[0].isupper():
                values.append(token)
    unique_values = dedupe_preserve_order(values)
    return len(values), unique_values[:25]


def lyric_features(title: str, lyrics: str) -> LyricFeatureSet:
    """Compute study-oriented mechanical lyric features.

    :param title: Song title.
    :param lyrics: Lyric text.
    :returns: Feature set instance.
    """

    text = lyrics.strip()
    raw_lines = text.splitlines()
    non_empty_lines = [line.strip() for line in raw_lines if line.strip()]
    stanza_count = len(re.split(r"\n\s*\n+", text)) if text else 0
    tokens = re.findall(r"[A-Za-z0-9']+", text.lower())
    unique_tokens = set(tokens)

    normalized_lines = [normalize_line(line) for line in non_empty_lines]
    normalized_lines = [line for line in normalized_lines if line]
    counts = Counter(normalized_lines)
    repeated_line_instances = sum(count - 1 for count in counts.values() if count > 1)

    pronoun_counts = {
        "first_person": sum(1 for token in tokens if token in FIRST_PERSON_PRONOUNS),
        "second_person": sum(1 for token in tokens if token in SECOND_PERSON_PRONOUNS),
        "third_person": sum(1 for token in tokens if token in THIRD_PERSON_PRONOUNS),
    }
    proper_noun_count, proper_nouns = proper_noun_stats(non_empty_lines)

    return LyricFeatureSet(
        text_length_chars=len(text),
        word_count=len(tokens),
        unique_word_ratio=round(len(unique_tokens) / len(tokens), 4) if tokens else None,
        line_count=len(non_empty_lines),
        stanza_count=stanza_count,
        repeated_line_ratio=round(repeated_line_instances / len(normalized_lines), 4)
        if normalized_lines
        else None,
        title_repetition_count=count_title_mentions(title, text),
        question_count=text.count("?"),
        pronoun_counts=pronoun_counts,
        proper_noun_count_heuristic=proper_noun_count,
        proper_nouns_heuristic=proper_nouns,
    )


def artist_match(query_artist: str, performer: str) -> bool:
    """Determine whether an artist query matches a chart performer.

    :param query_artist: Input artist.
    :param performer: Performer from chart source.
    :returns: ``True`` when the strings should be treated as a match.
    """

    query_norm = normalize_text(query_artist)
    performer_norm = normalize_text(performer)
    if not query_norm or not performer_norm:
        return False
    if query_norm == performer_norm:
        return True
    if query_norm in performer_norm or performer_norm in query_norm:
        return True
    query_tokens = set(query_norm.split())
    performer_tokens = set(performer_norm.split())
    if query_tokens and query_tokens.issubset(performer_tokens):
        return True
    return similarity(query_artist, performer) >= 0.78


def title_match(query_title: str, row_title: str) -> bool:
    """Determine whether a title query matches a chart title.

    :param query_title: Input title.
    :param row_title: Source title.
    :returns: ``True`` when the strings should be treated as a match.
    """

    return title_similarity(query_title, row_title) >= 0.92
