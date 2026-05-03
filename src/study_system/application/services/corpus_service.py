"""Corpus-building workflows."""

from __future__ import annotations

import csv
from pathlib import Path

from study_system.application.contracts import ChartSource
from study_system.application.dto import CorpusBuildRequest
from study_system.domain.models import CorpusEntry


class CorpusService:
    """Build corpus inputs for the study."""

    def __init__(self, chart_source: ChartSource) -> None:
        self.chart_source = chart_source

    def build_peak_corpus(self, request: CorpusBuildRequest) -> list[CorpusEntry]:
        """Build a corpus from peak weekly chart performance."""

        return self.chart_source.build_peak_corpus(
            list(request.years),
            request.top_n,
            selection_strategy=request.selection_strategy,
        )

    def load_corpus_csv(self, path: Path) -> list[CorpusEntry]:
        """Load a corpus definition CSV.

        :param path: CSV path with at least year, title, and artist columns.
        :returns: Corpus entries.
        """

        entries: list[CorpusEntry] = []
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                entries.append(
                    CorpusEntry(
                        year=int(row["year"]),
                        title=row["title"],
                        artist=row["artist"],
                        chart_rank=int(row["chart_rank"]) if row.get("chart_rank") else None,
                        chart_context_type=row.get("chart_context_type", "weekly_peak"),
                        source_chart_list=row.get("source_chart_list", "Billboard Hot 100 weekly archive"),
                    )
                )
        return entries
