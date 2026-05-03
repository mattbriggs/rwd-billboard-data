"""Unit tests for the local Billboard chart source."""

from __future__ import annotations

import csv
from pathlib import Path

from study_system.infrastructure.providers.chart_source import BillboardChartSource


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "hot-100-sample.csv"


def test_lookup_chart_context_returns_best_weekly_rank() -> None:
    source = BillboardChartSource(FIXTURE)
    summary = source.lookup_chart_context("Fast Car", "Tracy Chapman")
    assert summary.found is True
    assert summary.best_weekly_rank == 6
    assert summary.peak_year == 1988
    assert summary.entries_found == 3


def test_build_peak_corpus_sorts_by_best_rank() -> None:
    source = BillboardChartSource(FIXTURE)
    corpus = source.build_peak_corpus([1988], top_n=2, selection_strategy="peak_top_n")
    assert [entry.title for entry in corpus] == ["Roll With It", "Fast Car"]
    assert [entry.chart_rank for entry in corpus] == [1, 6]


def test_build_peak_corpus_stratifies_rank_bands(tmp_path: Path) -> None:
    path = tmp_path / "hot-100.csv"
    rows = [
        {"chart_week": "1988-01-02", "title": "One Hit", "performer": "Artist 1", "current_week": "1", "wks_on_chart": "10"},
        {"chart_week": "1988-01-09", "title": "Two Hit", "performer": "Artist 2", "current_week": "2", "wks_on_chart": "10"},
        {"chart_week": "1988-01-16", "title": "Seven Hit", "performer": "Artist 3", "current_week": "7", "wks_on_chart": "10"},
        {"chart_week": "1988-01-23", "title": "Fifteen Hit", "performer": "Artist 4", "current_week": "15", "wks_on_chart": "10"},
        {"chart_week": "1988-01-30", "title": "Thirty Hit", "performer": "Artist 5", "current_week": "30", "wks_on_chart": "10"},
        {"chart_week": "1988-02-06", "title": "Backup One", "performer": "Artist 6", "current_week": "1", "wks_on_chart": "10"},
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    source = BillboardChartSource(path)
    corpus = source.build_peak_corpus([1988], top_n=5, selection_strategy="stratified_peak")
    assert [entry.chart_rank for entry in corpus] == [1, 2, 7, 15, 30]
