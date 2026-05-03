"""Blind scoring workflows and score handling."""

from __future__ import annotations

from collections import defaultdict

from study_system.domain.models import ScoreCard, SongRecord
from study_system.domain.scoring import calculate_sci
from study_system.domain.scoring import heuristic_score_record
from study_system.domain.scoring import SCORE_FIELD_NAMES


class ScoringService:
    """Generate scoring packets and aggregate completed scores."""

    def export_score_packets(
        self,
        records: list[SongRecord],
        include_lyrics: bool = True,
        *,
        blind: bool = False,
    ) -> list[dict]:
        """Create scoring packets from enriched records.

        :param records: Enriched records.
        :param include_lyrics: Include lyric text if available.
        :param blind: Strip identifying and contextual fields for blind scoring.
        :returns: Packet payloads.
        """

        packets: list[dict] = []
        for record in records:
            if blind:
                packet = {
                    "song_id": record.song_id,
                    "title": record.title,
                    "lyric_features": record.lyric_features.to_dict() if record.lyric_features else None,
                    "lyrics_source_url": record.lyrics_source_url,
                }
                if include_lyrics and record.lyric_asset and record.lyric_asset.lyrics:
                    packet["lyrics_text"] = record.lyric_asset.lyrics
            else:
                packet = record.to_dict(include_lyrics=include_lyrics)
                packet["packet_mode"] = "full_context"
            packet["score_fields"] = list(SCORE_FIELD_NAMES)
            packet["speaker_situation_clarity"] = None
            packet["thematic_unity"] = None
            packet["image_motif_integration"] = None
            packet["structural_development"] = None
            packet["context_independence"] = None
            packet["scorer_id"] = None
            packet["notes"] = None
            packets.append(packet)
        return packets

    def export_blind_packets(self, records: list[SongRecord], include_lyrics: bool = False) -> list[dict]:
        """Create legacy blind scoring packets from enriched records."""

        return self.export_score_packets(records, include_lyrics=include_lyrics, blind=True)

    def complete_scores(
        self,
        records: list[SongRecord],
        scores: list[ScoreCard],
        *,
        auto_score_lyrics: bool = True,
    ) -> tuple[list[ScoreCard], dict[str, str], list[str]]:
        """Merge manual scores with deterministic fallback scores.

        :param records: Enriched records.
        :param scores: Completed manual or imported scores.
        :param auto_score_lyrics: Generate fallback scores for lyric-bearing records.
        :returns: Final score cards, score source map, and auto-scored song identifiers.
        """

        completed_scores = list(scores)
        score_map = {score.song_id: score for score in completed_scores}
        score_sources = {score.song_id: "manual" for score in completed_scores}
        auto_scored_song_ids: list[str] = []

        if not auto_score_lyrics:
            return completed_scores, score_sources, auto_scored_song_ids

        for record in records:
            if record.song_id in score_map:
                continue
            auto_score = heuristic_score_record(record)
            if auto_score is None:
                continue
            completed_scores.append(auto_score)
            score_map[record.song_id] = auto_score
            score_sources[record.song_id] = "auto_heuristic"
            auto_scored_song_ids.append(record.song_id)

        return completed_scores, score_sources, auto_scored_song_ids

    def summarize_scores(self, scores: list[ScoreCard]) -> list[dict]:
        """Summarize score cards by song identifier.

        :param scores: Score cards.
        :returns: Aggregate summary rows.
        """

        grouped: dict[str, list[ScoreCard]] = defaultdict(list)
        for score in scores:
            grouped[score.song_id].append(score)

        summaries: list[dict] = []
        for song_id, cards in grouped.items():
            sci_values = [calculate_sci(card) for card in cards]
            summaries.append(
                {
                    "song_id": song_id,
                    "ratings_count": len(cards),
                    "mean_sci": round(sum(sci_values) / len(sci_values), 4),
                    "scorer_ids": [card.scorer_id for card in cards],
                }
            )
        return summaries
