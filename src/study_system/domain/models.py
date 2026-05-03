"""Domain models for songs, lyrics, provenance, and scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProvenanceEntry:
    """Field provenance metadata.

    :param field_name: Name of the field being sourced.
    :param provider_name: Provider that supplied the field.
    :param source_ref: URL, file path, or provider identifier.
    :param confidence: Optional match confidence.
    """

    field_name: str
    provider_name: str
    source_ref: str
    confidence: float | None = None


@dataclass(frozen=True)
class LyricFeatureSet:
    """Mechanical lyric features used by the study.

    :param text_length_chars: Character count of lyric text.
    :param word_count: Token count.
    :param unique_word_ratio: Ratio of unique words to total tokens.
    :param line_count: Count of non-empty lines.
    :param stanza_count: Count of stanzas split on blank lines.
    :param repeated_line_ratio: Ratio of repeated lines to all normalized lines.
    :param title_repetition_count: Count of title phrase mentions.
    :param question_count: Count of question marks.
    :param pronoun_counts: First, second, and third person counts.
    :param proper_noun_count_heuristic: Heuristic proper noun count.
    :param proper_nouns_heuristic: Sample of heuristic proper nouns.
    """

    text_length_chars: int
    word_count: int
    unique_word_ratio: float | None
    line_count: int
    stanza_count: int
    repeated_line_ratio: float | None
    title_repetition_count: int
    question_count: int
    pronoun_counts: dict[str, int]
    proper_noun_count_heuristic: int
    proper_nouns_heuristic: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert the feature set to a dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class LyricAsset:
    """Lyric retrieval result.

    :param found: Whether lyric text was found.
    :param source: Provider name.
    :param source_url: URL used to retrieve the lyrics.
    :param query_title: Title variant used for provider lookup.
    :param query_artist: Artist variant used for provider lookup.
    :param lyrics: Optional lyric text.
    """

    found: bool
    source: str
    source_url: str | None
    query_title: str | None = None
    query_artist: str | None = None
    lyrics: str | None = None

    def without_text(self) -> "LyricAsset":
        """Return a copy without lyric text."""

        return LyricAsset(
            found=self.found,
            source=self.source,
            source_url=self.source_url,
            query_title=self.query_title,
            query_artist=self.query_artist,
            lyrics=None,
        )


@dataclass(frozen=True)
class ChartSummary:
    """Chart summary for a single song.

    :param found: Whether the song was found in the chart source.
    :param source_file: Backing chart file.
    :param matched_title: Matched title from source.
    :param matched_artist: Matched artist from source.
    :param entries_found: Number of rows matching title and artist.
    :param best_weekly_rank: Best weekly rank observed.
    :param best_chart_week: Week of best rank.
    :param peak_year: Release or chart year derived from best chart week.
    :param weeks_on_chart_max: Maximum weeks on chart observed.
    :param first_chart_week: First matching chart week.
    :param last_chart_week: Last matching chart week.
    """

    found: bool
    source_file: str
    matched_title: str | None = None
    matched_artist: str | None = None
    entries_found: int = 0
    best_weekly_rank: int | None = None
    best_chart_week: str | None = None
    peak_year: int | None = None
    weeks_on_chart_max: int | None = None
    first_chart_week: str | None = None
    last_chart_week: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the chart summary to a dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class MetadataSummary:
    """Metadata enrichment summary.

    :param matched: Whether the provider found a strong match.
    :param matched_title: Canonical title.
    :param matched_artist: Canonical artist.
    :param recording_id: Provider recording identifier.
    :param recording_length_ms: Recording duration in milliseconds.
    :param first_release_date: First release date.
    :param first_release_year: Derived release year.
    :param genres: Genre candidates.
    :param tags: Provider tags.
    :param labels: Label names.
    :param songwriters: Writer names.
    :param lyricists: Lyricist names.
    :param composers: Composer names.
    :param producers: Producer names.
    :param writer_count: Number of deduplicated writers.
    :param producer_count: Number of deduplicated producers.
    :param is_cover: Cover indicator.
    :param has_sample: Sampling or interpolation indicator.
    :param recording_url: Provider recording URL.
    :param release: Release payload.
    :param works: Related work payloads.
    :param search_query: Original query values.
    """

    matched: bool
    matched_title: str | None = None
    matched_artist: str | None = None
    recording_id: str | None = None
    recording_length_ms: int | None = None
    first_release_date: str | None = None
    first_release_year: int | None = None
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    songwriters: list[str] = field(default_factory=list)
    lyricists: list[str] = field(default_factory=list)
    composers: list[str] = field(default_factory=list)
    producers: list[str] = field(default_factory=list)
    writer_count: int | None = None
    producer_count: int | None = None
    is_cover: bool | None = None
    has_sample: bool | None = None
    recording_url: str | None = None
    release: dict[str, Any] = field(default_factory=dict)
    works: list[dict[str, Any]] = field(default_factory=list)
    search_query: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the metadata summary to a dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class CorpusEntry:
    """Corpus row used for batch enrichment.

    :param year: Study year.
    :param title: Song title.
    :param artist: Artist name.
    :param chart_rank: Best chart rank within the chosen source.
    :param chart_context_type: Weekly or year-end context.
    :param source_chart_list: Human-readable chart source label.
    """

    year: int
    title: str
    artist: str
    chart_rank: int | None = None
    chart_context_type: str = "weekly_peak"
    source_chart_list: str = "Billboard Hot 100 weekly archive"

    def to_dict(self) -> dict[str, Any]:
        """Convert the corpus entry to a dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class ScoreCard:
    """Human or model-generated scoring card.

    :param song_id: Associated record identifier.
    :param speaker_situation_clarity: Score from 0 to 2.
    :param thematic_unity: Score from 0 to 2.
    :param image_motif_integration: Score from 0 to 2.
    :param structural_development: Score from 0 to 2.
    :param context_independence: Score from 0 to 2.
    :param scorer_id: Rater or system identifier.
    :param notes: Optional scoring notes.
    """

    song_id: str
    speaker_situation_clarity: int
    thematic_unity: int
    image_motif_integration: int
    structural_development: int
    context_independence: int
    scorer_id: str = "unknown"
    notes: str | None = None

    @property
    def self_containment_index(self) -> int:
        """Return the total Self-Containment Index."""

        return (
            self.speaker_situation_clarity
            + self.thematic_unity
            + self.image_motif_integration
            + self.structural_development
            + self.context_independence
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the score card to a dictionary."""

        payload = asdict(self)
        payload["self_containment_index"] = self.self_containment_index
        return payload


@dataclass(frozen=True)
class SongRecord:
    """Fully enriched song record.

    :param song_id: Stable identifier used throughout exports and scoring.
    :param query_title: Original query title.
    :param query_artist: Original query artist.
    :param title: Best matched title.
    :param artist: Best matched artist.
    :param year: Study or release year.
    :param chart_rank: Best weekly chart rank.
    :param source_chart_list: Chart source label.
    :param genre: Genre candidates.
    :param songwriters: Songwriter candidates.
    :param producers: Producer candidates.
    :param label: Label candidates.
    :param writer_count: Writer count.
    :param producer_count: Producer count.
    :param is_cover: Cover indicator.
    :param has_sample: Sample indicator.
    :param lyrics_source_url: Source URL for lyric lookup.
    :param lyrics_found: Whether lyrics were found.
    :param recording_length_ms: Recording duration.
    :param first_release_date: First release date.
    :param billboard_best_chart_week: Week of best rank.
    :param billboard_weeks_on_chart_max: Maximum weeks on chart.
    :param lyric_features: Optional feature set.
    :param lyric_asset: Optional lyric asset.
    :param metadata_summary: Raw metadata summary for audit.
    :param chart_summary: Raw chart summary for audit.
    :param provenance: Provenance entries.
    :param errors: Recoverable lookup errors.
    """

    song_id: str
    query_title: str
    query_artist: str
    title: str
    artist: str
    year: int | None
    chart_rank: int | None
    source_chart_list: str
    genre: list[str]
    songwriters: list[str]
    producers: list[str]
    label: list[str]
    writer_count: int | None
    producer_count: int | None
    is_cover: bool | None
    has_sample: bool | None
    lyrics_source_url: str | None
    lyrics_found: bool
    recording_length_ms: int | None
    first_release_date: str | None
    billboard_best_chart_week: str | None
    billboard_weeks_on_chart_max: int | None
    lyric_features: LyricFeatureSet | None = None
    lyric_asset: LyricAsset | None = None
    metadata_summary: MetadataSummary | None = None
    chart_summary: ChartSummary | None = None
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def lyrics_text(self) -> str | None:
        """Return full lyric text when available."""

        if self.lyric_asset is None:
            return None
        return self.lyric_asset.lyrics

    def to_dict(self, include_lyrics: bool = False) -> dict[str, Any]:
        """Convert the song record to a dictionary.

        :param include_lyrics: Include lyric text when available.
        :returns: JSON-serializable representation.
        """

        payload: dict[str, Any] = {
            "song_id": self.song_id,
            "query_title": self.query_title,
            "query_artist": self.query_artist,
            "title": self.title,
            "artist": self.artist,
            "year": self.year,
            "chart_rank": self.chart_rank,
            "source_chart_list": self.source_chart_list,
            "genre": self.genre,
            "songwriters": self.songwriters,
            "producers": self.producers,
            "label": self.label,
            "writer_count": self.writer_count,
            "producer_count": self.producer_count,
            "is_cover": self.is_cover,
            "has_sample": self.has_sample,
            "lyrics_source_url": self.lyrics_source_url,
            "lyrics_found": self.lyrics_found,
            "recording_length_ms": self.recording_length_ms,
            "first_release_date": self.first_release_date,
            "billboard_best_chart_week": self.billboard_best_chart_week,
            "billboard_weeks_on_chart_max": self.billboard_weeks_on_chart_max,
            "lyrics_text": self.lyrics_text if include_lyrics else None,
            "provenance": [asdict(item) for item in self.provenance],
            "errors": list(self.errors),
        }
        if self.lyric_features is not None:
            payload["lyric_features"] = self.lyric_features.to_dict()
        if self.lyric_asset is not None:
            payload["lyric_asset"] = asdict(self.lyric_asset.without_text())
        if self.metadata_summary is not None:
            payload["metadata_summary"] = self.metadata_summary.to_dict()
        if self.chart_summary is not None:
            payload["chart_summary"] = self.chart_summary.to_dict()
        return payload
