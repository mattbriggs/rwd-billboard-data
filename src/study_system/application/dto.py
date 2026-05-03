"""Application data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class LookupRequest:
    """Lookup input for a single song.

    :param title: Song title.
    :param artist: Artist name.
    :param billboard_file: Chart file used for local context.
    :param include_lyrics: Include lyric text in persisted output.
    """

    title: str
    artist: str
    billboard_file: Path
    include_lyrics: bool = False


@dataclass(frozen=True)
class CorpusBuildRequest:
    """Batch corpus build request.

    :param years: Selected study years.
    :param top_n: Number of songs to keep per year.
    :param selection_strategy: Corpus sampling strategy.
    """

    years: Sequence[int]
    top_n: int
    selection_strategy: str = "stratified_peak"


@dataclass(frozen=True)
class OutputRequest:
    """Generic output request.

    :param output: Output file path.
    :param pretty: Pretty-print JSON output.
    """

    output: Path
    pretty: bool = False
