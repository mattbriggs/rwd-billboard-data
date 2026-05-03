"""Unit tests for corpus workflows."""

from __future__ import annotations

from pathlib import Path

from study_system.application.dto import CorpusBuildRequest
from study_system.application.services.corpus_service import CorpusService
from study_system.domain.models import CorpusEntry


class FakeChartSource:
    def build_peak_corpus(
        self,
        years: list[int],
        top_n: int,
        selection_strategy: str = "stratified_peak",
    ) -> list[CorpusEntry]:
        return [CorpusEntry(year=years[0], title="Fast Car", artist="Tracy Chapman", chart_rank=6)]


def test_build_peak_corpus_delegates_to_chart_source() -> None:
    service = CorpusService(FakeChartSource())
    corpus = service.build_peak_corpus(CorpusBuildRequest(years=[1988], top_n=25))
    assert corpus[0].title == "Fast Car"


def test_load_corpus_csv_reads_expected_rows(tmp_path: Path) -> None:
    path = tmp_path / "corpus.csv"
    path.write_text(
        "year,title,artist,chart_rank\n1988,Fast Car,Tracy Chapman,6\n",
        encoding="utf-8",
    )
    entries = CorpusService(FakeChartSource()).load_corpus_csv(path)
    assert entries[0].artist == "Tracy Chapman"
