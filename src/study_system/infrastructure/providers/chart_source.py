"""Local Billboard chart source adapter."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from study_system.domain.feature_rules import artist_match, first_year_from_text, safe_int, title_match
from study_system.domain.models import ChartSummary, CorpusEntry

STRATIFIED_RANK_BUCKETS = (
    (1, 1),
    (2, 5),
    (6, 10),
    (11, 25),
    (26, 50),
)


class BillboardChartSource:
    """Read chart context from the local Hot 100 archive.

    :param csv_path: Chart CSV path.
    """

    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path

    def _load_rows(self) -> list[dict[str, str]]:
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def lookup_chart_context(self, title: str, artist: str) -> ChartSummary:
        """Lookup chart context for a single title and artist pair."""

        matches: list[dict[str, str]] = []
        for row in self._load_rows():
            if title_match(title, row.get("title", "")) and artist_match(artist, row.get("performer", "")):
                matches.append(row)

        if not matches:
            return ChartSummary(found=False, source_file=str(self.csv_path))

        peak_row = min(
            matches,
            key=lambda row: (
                safe_int(row.get("current_week")) if safe_int(row.get("current_week")) is not None else 999,
                row.get("chart_week") or "9999-99-99",
            ),
        )
        chart_weeks = [row.get("chart_week") for row in matches if row.get("chart_week")]
        max_weeks = max((safe_int(row.get("wks_on_chart")) or 0) for row in matches)
        return ChartSummary(
            found=True,
            source_file=str(self.csv_path),
            matched_title=peak_row.get("title"),
            matched_artist=peak_row.get("performer"),
            entries_found=len(matches),
            best_weekly_rank=safe_int(peak_row.get("current_week")),
            best_chart_week=peak_row.get("chart_week"),
            peak_year=first_year_from_text(peak_row.get("chart_week")),
            weeks_on_chart_max=max_weeks,
            first_chart_week=min(chart_weeks) if chart_weeks else None,
            last_chart_week=max(chart_weeks) if chart_weeks else None,
        )

    def build_peak_corpus(
        self,
        years: list[int],
        top_n: int,
        selection_strategy: str = "stratified_peak",
    ) -> list[CorpusEntry]:
        """Build a corpus of songs by best weekly chart rank within each year."""

        rows = self._load_rows()
        grouped: dict[int, dict[tuple[str, str], dict[str, str | int]]] = defaultdict(dict)

        for row in rows:
            chart_week = row.get("chart_week")
            year = first_year_from_text(chart_week)
            if year not in years:
                continue
            key = (row["title"], row["performer"])
            current_rank = safe_int(row.get("current_week")) or 999
            existing = grouped[year].get(key)
            candidate = {
                "title": row["title"],
                "artist": row["performer"],
                "best_weekly_rank": current_rank,
                "best_chart_week": row.get("chart_week") or "",
            }
            if existing is None:
                grouped[year][key] = candidate
                continue
            existing_rank = int(existing["best_weekly_rank"])
            existing_week = str(existing["best_chart_week"])
            if current_rank < existing_rank or (current_rank == existing_rank and str(candidate["best_chart_week"]) < existing_week):
                grouped[year][key] = candidate

        corpus: list[CorpusEntry] = []
        for year in years:
            songs = self._select_yearly_songs(list(grouped[year].values()), top_n, selection_strategy)
            corpus.extend(
                CorpusEntry(
                    year=year,
                    title=str(item["title"]),
                    artist=str(item["artist"]),
                    chart_rank=int(item["best_weekly_rank"]),
                )
                for item in songs
            )
        return corpus

    def _select_yearly_songs(
        self,
        items: list[dict[str, str | int]],
        top_n: int,
        selection_strategy: str,
    ) -> list[dict[str, str | int]]:
        """Select yearly corpus rows according to a sampling strategy."""

        ranked = sorted(
            items,
            key=lambda item: (int(item["best_weekly_rank"]), str(item["best_chart_week"]), str(item["title"])),
        )
        if selection_strategy == "peak_top_n":
            return ranked[:top_n]
        if selection_strategy != "stratified_peak":
            raise ValueError(f"Unknown selection strategy: {selection_strategy}")

        quota_base = top_n // len(STRATIFIED_RANK_BUCKETS)
        quota_remainder = top_n % len(STRATIFIED_RANK_BUCKETS)
        selected_keys: set[tuple[str, str]] = set()
        selected: list[dict[str, str | int]] = []

        for index, (rank_min, rank_max) in enumerate(STRATIFIED_RANK_BUCKETS):
            bucket_quota = quota_base + (1 if index < quota_remainder else 0)
            if bucket_quota <= 0:
                continue
            bucket_items = [
                item
                for item in ranked
                if rank_min <= int(item["best_weekly_rank"]) <= rank_max
                and self._selection_key(item) not in selected_keys
            ]
            for item in bucket_items[:bucket_quota]:
                selected.append(item)
                selected_keys.add(self._selection_key(item))

        if len(selected) < top_n:
            for item in ranked:
                key = self._selection_key(item)
                if key in selected_keys:
                    continue
                selected.append(item)
                selected_keys.add(key)
                if len(selected) >= top_n:
                    break

        return selected[:top_n]

    def _selection_key(self, item: dict[str, str | int]) -> tuple[str, str]:
        """Create a stable uniqueness key for corpus row selection."""

        return (str(item["title"]), str(item["artist"]))
