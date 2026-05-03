"""Abstract contracts for providers and repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from study_system.domain.models import ChartSummary, CorpusEntry, LyricAsset, MetadataSummary, ScoreCard, SongRecord


class ChartSource(Protocol):
    """Chart source contract."""

    def lookup_chart_context(self, title: str, artist: str) -> ChartSummary:
        """Lookup chart context for a single song."""

    def build_peak_corpus(
        self,
        years: Sequence[int],
        top_n: int,
        selection_strategy: str = "stratified_peak",
    ) -> list[CorpusEntry]:
        """Build a corpus based on peak weekly performance."""


class MetadataProvider(Protocol):
    """Metadata provider contract."""

    def lookup_metadata(self, title: str, artist: str) -> MetadataSummary:
        """Return metadata enrichment summary."""


class LyricsProvider(Protocol):
    """Lyrics provider contract."""

    def lookup_lyrics(self, title: str, artist: str, metadata: MetadataSummary) -> LyricAsset:
        """Return lyric asset for a song."""


class SongRepository(Protocol):
    """Persistence contract for enriched song records."""

    def save_records(self, path: Path, records: Sequence[SongRecord], include_lyrics: bool = False) -> None:
        """Persist song records."""

    def load_records(self, path: Path) -> list[SongRecord]:
        """Load persisted song records."""


class ScoreRepository(Protocol):
    """Persistence contract for score cards."""

    def save_scores(self, path: Path, scores: Sequence[ScoreCard]) -> None:
        """Persist score cards."""

    def load_scores(self, path: Path) -> list[ScoreCard]:
        """Load score cards."""
