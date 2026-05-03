"""MusicBrainz metadata adapter."""

from __future__ import annotations

from urllib.parse import urlencode

from study_system.domain.feature_rules import (
    collect_names_from_genre_objects,
    dedupe_preserve_order,
    extract_relation_artists,
    first_year_from_text,
    parse_artist_credit,
    relation_flags,
    safe_int,
    similarity,
    title_similarity,
)
from study_system.domain.models import MetadataSummary
from study_system.infrastructure.http.client import JsonHttpClient
from study_system.infrastructure.persistence.cache_store import JsonCacheStore

MUSICBRAINZ_ROOT = "https://musicbrainz.org/ws/2"


class MusicBrainzMetadataProvider:
    """Fetch song metadata from MusicBrainz.

    :param http_client: JSON HTTP client.
    :param cache_store: Optional filesystem cache.
    """

    def __init__(self, http_client: JsonHttpClient, cache_store: JsonCacheStore | None = None) -> None:
        self.http_client = http_client
        self.cache_store = cache_store

    def _fetch_json(self, url: str) -> dict:
        if self.cache_store is not None:
            cached = self.cache_store.get(url)
            if cached is not None:
                return cached
        payload = self.http_client.fetch_json(url, rate_limit_key="musicbrainz", min_interval=1.0)
        if self.cache_store is not None:
            self.cache_store.set(url, payload)
        return payload

    def _search_recording(self, title: str, artist: str) -> dict | None:
        query = f'recording:"{title}" AND artist:"{artist}"'
        url = f"{MUSICBRAINZ_ROOT}/recording?{urlencode({'query': query, 'fmt': 'json', 'limit': 10})}"
        payload = self._fetch_json(url)
        recordings = payload.get("recordings") or []
        if not recordings:
            return None

        def candidate_score(recording: dict) -> float:
            mb_score = (safe_int(recording.get("score")) or 0) / 100.0
            title_score = title_similarity(title, recording.get("title", ""))
            artist_score = similarity(artist, parse_artist_credit(recording.get("artist-credit")))
            return (0.45 * mb_score) + (0.35 * title_score) + (0.20 * artist_score)

        return max(recordings, key=candidate_score)

    def _fetch_recording(self, recording_id: str) -> dict:
        inc = "artist-credits+releases+release-groups+genres+tags+isrcs+work-rels+artist-rels+release-rels+url-rels"
        url = f"{MUSICBRAINZ_ROOT}/recording/{recording_id}?{urlencode({'inc': inc, 'fmt': 'json'})}"
        return self._fetch_json(url)

    def _fetch_release(self, release_id: str) -> dict:
        inc = "labels+artist-credits+artist-rels+genres+tags+url-rels"
        url = f"{MUSICBRAINZ_ROOT}/release/{release_id}?{urlencode({'inc': inc, 'fmt': 'json'})}"
        return self._fetch_json(url)

    def _fetch_work(self, work_id: str) -> dict:
        inc = "artist-rels+genres+tags+aliases+url-rels"
        url = f"{MUSICBRAINZ_ROOT}/work/{work_id}?{urlencode({'inc': inc, 'fmt': 'json'})}"
        return self._fetch_json(url)

    @staticmethod
    def _choose_earliest_release(releases: list[dict]) -> dict | None:
        if not releases:
            return None
        return sorted(
            releases,
            key=lambda item: (
                first_year_from_text(item.get("date")) or 9999,
                item.get("date") or "9999-99-99",
                item.get("title") or "",
            ),
        )[0]

    def lookup_metadata(self, title: str, artist: str) -> MetadataSummary:
        """Lookup metadata for a single song."""

        search_hit = self._search_recording(title, artist)
        if not search_hit:
            return MetadataSummary(matched=False, search_query={"title": title, "artist": artist})

        recording = self._fetch_recording(search_hit["id"])
        release = self._choose_earliest_release(recording.get("releases") or [])
        release_detail = self._fetch_release(release["id"]) if release else None

        work_summaries: list[dict] = []
        songwriters: list[str] = []
        lyricists: list[str] = []
        composers: list[str] = []
        writer_like_types = {"writer"}
        lyricist_types = {"lyricist"}
        composer_types = {"composer"}
        producer_type_fragments = ("producer",)

        recording_relations = recording.get("relations") or []
        rel_flags = relation_flags(recording_relations)

        for relation in [relation for relation in recording_relations if relation.get("work")]:
            work_stub = relation.get("work") or {}
            work_id = work_stub.get("id")
            if not work_id:
                continue
            work_detail = self._fetch_work(work_id)
            work_artist_relations = work_detail.get("relations") or []
            relation_writer_flags = relation_flags(work_artist_relations)
            rel_flags["is_cover"] = rel_flags["is_cover"] or relation_writer_flags["is_cover"]
            rel_flags["has_sample"] = rel_flags["has_sample"] or relation_writer_flags["has_sample"]
            work_writers = extract_relation_artists(work_artist_relations, matching_types=writer_like_types)
            work_lyricists = extract_relation_artists(work_artist_relations, matching_types=lyricist_types)
            work_composers = extract_relation_artists(work_artist_relations, matching_types=composer_types)
            songwriters.extend(work_writers)
            lyricists.extend(work_lyricists)
            composers.extend(work_composers)
            work_summaries.append(
                {
                    "id": work_detail.get("id"),
                    "title": work_detail.get("title"),
                    "type": work_detail.get("type"),
                    "genres": collect_names_from_genre_objects(work_detail.get("genres")),
                    "tags": collect_names_from_genre_objects(work_detail.get("tags")),
                    "writers": work_writers,
                    "lyricists": work_lyricists,
                    "composers": work_composers,
                    "musicbrainz_url": f"https://musicbrainz.org/work/{work_detail.get('id')}",
                }
            )

        recording_producers = extract_relation_artists(recording_relations, contains_any=producer_type_fragments)
        release_relations = (release_detail or {}).get("relations") or []
        release_producers = extract_relation_artists(release_relations, contains_any=producer_type_fragments)
        labels = dedupe_preserve_order(
            [
                item.get("label", {}).get("name", "")
                for item in (release_detail or {}).get("label-info") or []
                if item.get("label")
            ]
        )
        genres = dedupe_preserve_order(
            collect_names_from_genre_objects(recording.get("genres"))
            + collect_names_from_genre_objects((release_detail or {}).get("genres"))
            + collect_names_from_genre_objects(recording.get("tags"))[:5]
        )

        artist_name = parse_artist_credit(recording.get("artist-credit"))
        all_songwriters = dedupe_preserve_order(songwriters + lyricists + composers)
        all_producers = dedupe_preserve_order(recording_producers + release_producers)

        return MetadataSummary(
            matched=True,
            matched_title=recording.get("title"),
            matched_artist=artist_name,
            recording_id=recording.get("id"),
            recording_length_ms=safe_int(recording.get("length")),
            first_release_date=recording.get("first-release-date"),
            first_release_year=first_year_from_text(recording.get("first-release-date")),
            genres=genres,
            tags=collect_names_from_genre_objects(recording.get("tags")),
            labels=labels,
            songwriters=all_songwriters,
            lyricists=dedupe_preserve_order(lyricists),
            composers=dedupe_preserve_order(composers),
            producers=all_producers,
            writer_count=len(all_songwriters),
            producer_count=len(all_producers),
            is_cover=rel_flags["is_cover"],
            has_sample=rel_flags["has_sample"],
            recording_url=f"https://musicbrainz.org/recording/{recording.get('id')}",
            release={
                "id": release_detail.get("id") if release_detail else release.get("id") if release else None,
                "title": release_detail.get("title") if release_detail else release.get("title") if release else None,
                "date": release_detail.get("date") if release_detail else release.get("date") if release else None,
                "status": release_detail.get("status") if release_detail else release.get("status") if release else None,
                "country": release_detail.get("country") if release_detail else release.get("country") if release else None,
                "labels": labels,
            },
            works=work_summaries,
            search_query={"title": title, "artist": artist},
        )
