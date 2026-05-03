"""Command-line interface for the study system."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from study_system.application.dto import LookupRequest
from study_system.application.dto import CorpusBuildRequest
from study_system.application.services.corpus_service import CorpusService
from study_system.application.services.enrichment_service import EnrichmentService
from study_system.application.services.export_service import ExportService
from study_system.application.services.scoring_service import ScoringService
from study_system.config.logging_config import configure_logging
from study_system.config.settings import discover_settings
from study_system.domain.models import ScoreCard
from study_system.infrastructure.http.client import JsonHttpClient
from study_system.infrastructure.persistence.cache_store import JsonCacheStore
from study_system.infrastructure.persistence.repositories import InvalidScoreFileError
from study_system.infrastructure.persistence.repositories import JsonScoreRepository, JsonSongRepository
from study_system.infrastructure.providers.chart_source import BillboardChartSource
from study_system.infrastructure.providers.chained_lyrics_provider import ChainedLyricsProvider
from study_system.infrastructure.providers.lyrics_provider import LyricsOvhProvider
from study_system.infrastructure.providers.musicbrainz_provider import MusicBrainzMetadataProvider
from study_system.infrastructure.providers.musixmatch_provider import MusixmatchLyricsProvider

USER_AGENT = "study-system/0.1 (research metadata collector)"


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    settings = discover_settings()
    parser = argparse.ArgumentParser(description="Music study data collection and scoring CLI.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    lookup = subparsers.add_parser("lookup", help="Lookup a single song.")
    lookup.add_argument("--title", required=True)
    lookup.add_argument("--artist", required=True)
    lookup.add_argument("--billboard-file", default=str(settings.default_billboard_file))
    lookup.add_argument("--include-lyrics", action="store_true")
    lookup.add_argument("--output")
    lookup.add_argument("--pretty", action="store_true")

    build_corpus = subparsers.add_parser("build-corpus", help="Build a corpus from chart peaks.")
    build_corpus.add_argument("--years", nargs="+", type=int, required=True)
    build_corpus.add_argument("--top-n", type=int, default=25)
    build_corpus.add_argument("--billboard-file", default=str(settings.default_billboard_file))
    build_corpus.add_argument(
        "--selection-strategy",
        choices=["stratified_peak", "peak_top_n"],
        default="stratified_peak",
        help="Corpus selection mode. Defaults to a less #1-heavy stratified peak sample.",
    )
    build_corpus.add_argument("--output", required=True)

    enrich = subparsers.add_parser("enrich", help="Enrich a corpus CSV or JSON.")
    enrich.add_argument("--corpus-file", required=True)
    enrich.add_argument("--billboard-file", default=str(settings.default_billboard_file))
    enrich.add_argument("--output", required=True)
    enrich_lyrics = enrich.add_mutually_exclusive_group()
    enrich_lyrics.add_argument(
        "--include-lyrics",
        dest="include_lyrics",
        action="store_true",
        help="Persist full lyrics in enriched records. This is the default for enrich.",
    )
    enrich_lyrics.add_argument(
        "--omit-lyrics",
        dest="include_lyrics",
        action="store_false",
        help="Skip lyric text persistence in enriched records.",
    )
    enrich.set_defaults(include_lyrics=True)

    packets = subparsers.add_parser("score-packets", help="Export blind scoring packets.")
    packets.add_argument("--records-file", required=True)
    packets.add_argument("--output", required=True)
    packet_lyrics = packets.add_mutually_exclusive_group()
    packet_lyrics.add_argument(
        "--include-lyrics",
        dest="include_lyrics",
        action="store_true",
        help="Include lyric text in scoring packets. This is the default.",
    )
    packet_lyrics.add_argument(
        "--omit-lyrics",
        dest="include_lyrics",
        action="store_false",
        help="Skip lyric text in scoring packets.",
    )
    packets.add_argument(
        "--blind",
        action="store_true",
        help="Strip identifying and contextual fields for blind scoring packets.",
    )
    packets.set_defaults(include_lyrics=True)

    export = subparsers.add_parser("export-dataset", help="Export final joined dataset.")
    export.add_argument("--records-file", required=True)
    export.add_argument("--scores-file", required=True)
    export.add_argument("--output", required=True)
    export.add_argument(
        "--strict-scores",
        action="store_true",
        help="Fail if the scores file contains incomplete scoring packets.",
    )

    return parser


def _build_enrichment_service(billboard_file: Path) -> EnrichmentService:
    settings = discover_settings()
    cache = JsonCacheStore(settings.cache_dir)
    http_client = JsonHttpClient(user_agent=USER_AGENT)
    chart_source = BillboardChartSource(billboard_file)
    metadata_provider = MusicBrainzMetadataProvider(http_client=http_client, cache_store=cache)
    lyrics_providers = []
    if settings.musixmatch_api_key:
        lyrics_providers.append(
            MusixmatchLyricsProvider(
                http_client=http_client,
                api_key=settings.musixmatch_api_key,
                cache_store=cache,
            )
        )
    lyrics_providers.append(LyricsOvhProvider(http_client=http_client, cache_store=cache))
    lyrics_provider = ChainedLyricsProvider(lyrics_providers)
    return EnrichmentService(chart_source, metadata_provider, lyrics_provider)


def _print_or_write(payload, output: str | None, pretty: bool) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    if output:
        Path(output).write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
        return
    print(text)


def _load_corpus_entries(path: Path) -> list[tuple[int, str, str]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [(int(item["year"]), item["title"], item["artist"]) for item in payload]
    entries: list[tuple[int, str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            entries.append((int(row["year"]), row["title"], row["artist"]))
    return entries


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    :param argv: Optional command-line arguments.
    :returns: Process exit status.
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    if args.command == "lookup":
        service = _build_enrichment_service(Path(args.billboard_file))
        record = service.lookup_song(
            LookupRequest(
                title=args.title,
                artist=args.artist,
                billboard_file=Path(args.billboard_file),
                include_lyrics=args.include_lyrics,
            )
        )
        _print_or_write(record.to_dict(include_lyrics=args.include_lyrics), args.output, args.pretty)
        return 0

    if args.command == "build-corpus":
        chart_source = BillboardChartSource(Path(args.billboard_file))
        service = CorpusService(chart_source)
        corpus = service.build_peak_corpus(
            CorpusBuildRequest(
                years=args.years,
                top_n=args.top_n,
                selection_strategy=args.selection_strategy,
            )
        )
        ExportService().export_json(Path(args.output), [entry.to_dict() for entry in corpus], pretty=True)
        return 0

    if args.command == "enrich":
        service = _build_enrichment_service(Path(args.billboard_file))
        entries = _load_corpus_entries(Path(args.corpus_file))
        records = service.enrich_corpus(entries, args.include_lyrics, Path(args.billboard_file))
        JsonSongRepository().save_records(Path(args.output), records, include_lyrics=args.include_lyrics)
        return 0

    if args.command == "score-packets":
        records = JsonSongRepository().load_records(Path(args.records_file))
        packets = ScoringService().export_score_packets(
            records,
            include_lyrics=args.include_lyrics,
            blind=args.blind,
        )
        ExportService().export_json(Path(args.output), packets, pretty=True)
        return 0

    if args.command == "export-dataset":
        records = JsonSongRepository().load_records(Path(args.records_file))
        try:
            score_repository = JsonScoreRepository()
            if args.strict_scores:
                scores = score_repository.load_scores(Path(args.scores_file))
                skipped_song_ids: list[str] = []
            else:
                scores, skipped_song_ids = score_repository.load_scores_with_report(
                    Path(args.scores_file),
                    skip_incomplete=True,
                )
        except InvalidScoreFileError as exc:
            parser.exit(2, f"error: {exc}\n")
        scores, score_sources, auto_scored_song_ids = ScoringService().complete_scores(records, scores)
        ExportService().export_final_dataset(
            Path(args.output),
            records,
            scores,
            score_sources=score_sources,
        )
        if skipped_song_ids:
            sample = ", ".join(skipped_song_ids[:5])
            suffix = "" if len(skipped_song_ids) <= 5 else ", ..."
            print(
                "warning: "
                f"Skipped {len(skipped_song_ids)} incomplete scoring packet(s) from "
                f"'{args.scores_file}' and exported blank score columns for those songs: "
                f"{sample}{suffix}",
                file=sys.stderr,
            )
        if auto_scored_song_ids:
            print(
                "warning: "
                f"Generated fallback heuristic scores for {len(auto_scored_song_ids)} lyric-bearing song(s) "
                f"that did not have completed manual scores.",
                file=sys.stderr,
            )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
