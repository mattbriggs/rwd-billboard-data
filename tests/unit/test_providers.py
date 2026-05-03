"""Unit tests for metadata and lyrics providers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError

from study_system.domain.models import MetadataSummary
from study_system.infrastructure.persistence.cache_store import JsonCacheStore
from study_system.infrastructure.providers.chained_lyrics_provider import ChainedLyricsProvider
from study_system.infrastructure.providers.lyrics_provider import LyricsOvhProvider
from study_system.infrastructure.providers.musicbrainz_provider import MusicBrainzMetadataProvider
from study_system.infrastructure.providers.musixmatch_provider import MusixmatchLyricsProvider


class FakeHttpClient:
    def __init__(self, payloads):
        self.payloads = payloads

    def fetch_json(self, url: str, *, rate_limit_key: str | None = None, min_interval: float = 0.0):
        for key, value in self.payloads.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError(f"Unexpected URL: {url}")


def test_lyrics_provider_returns_found_asset() -> None:
    provider = LyricsOvhProvider(
        http_client=FakeHttpClient({"api.lyrics.ovh": {"lyrics": "Fast car"}}),
        cache_store=None,
    )
    metadata = MetadataSummary(matched=True, matched_title="Fast Car", matched_artist="Tracy Chapman")
    asset = provider.lookup_lyrics("Fast Car", "Tracy Chapman", metadata)
    assert asset.found is True
    assert asset.lyrics == "Fast car"


def test_lyrics_provider_handles_missing_lyrics() -> None:
    missing = HTTPError("https://example.test", 404, "not found", hdrs=None, fp=None)
    provider = LyricsOvhProvider(http_client=FakeHttpClient({"api.lyrics.ovh": missing}), cache_store=None)
    metadata = MetadataSummary(matched=True, matched_title="Fast Car", matched_artist="Tracy Chapman")
    asset = provider.lookup_lyrics("Fast Car", "Tracy Chapman", metadata)
    assert asset.found is False


def test_lyrics_provider_caches_compact_bulk_analysis_payload(tmp_path: Path) -> None:
    cache = JsonCacheStore(tmp_path)
    provider = LyricsOvhProvider(
        http_client=FakeHttpClient({"api.lyrics.ovh": {"lyrics": "Fast car"}}),
        cache_store=cache,
    )
    metadata = MetadataSummary(matched=True, matched_title="Fast Car", matched_artist="Tracy Chapman")

    asset = provider.lookup_lyrics("Fast Car", "Tracy Chapman", metadata)

    url = "https://api.lyrics.ovh/v1/Tracy%20Chapman/Fast%20Car"
    cached = cache.get(url)
    assert asset.lyrics == "Fast car"
    assert cached == {
        "lyrics_text": "Fast car",
        "source": "lyrics.ovh",
        "source_url": url,
    }


def test_chained_lyrics_provider_falls_through_to_next_provider() -> None:
    @dataclass
    class FakeProvider:
        found: bool
        source: str

        def lookup_lyrics(self, title: str, artist: str, metadata: MetadataSummary):
            from study_system.domain.models import LyricAsset

            return LyricAsset(
                found=self.found,
                source=self.source,
                source_url=f"https://example.test/{self.source}",
                lyrics="Fast car" if self.found else None,
            )

    provider = ChainedLyricsProvider([FakeProvider(False, "first"), FakeProvider(True, "second")])
    metadata = MetadataSummary(matched=True, matched_title="Fast Car", matched_artist="Tracy Chapman")
    asset = provider.lookup_lyrics("Fast Car", "Tracy Chapman", metadata)
    assert asset.found is True
    assert asset.source == "second"


def test_musixmatch_provider_returns_cleaned_lyrics() -> None:
    payloads = {
        "/matcher.track.get": {
            "message": {
                "body": {
                    "track": {
                        "track_id": 123,
                        "track_share_url": "https://www.musixmatch.com/lyrics/artist/song",
                    }
                }
            }
        },
        "/track.lyrics.get": {
            "message": {
                "body": {
                    "lyrics": {
                        "lyrics_body": "Fast car\nFast car\n******* This Lyrics is NOT for Commercial use *******"
                    }
                }
            }
        },
    }
    provider = MusixmatchLyricsProvider(
        http_client=FakeHttpClient(payloads),
        api_key="token",
        cache_store=None,
    )
    metadata = MetadataSummary(matched=True, matched_title="Fast Car", matched_artist="Tracy Chapman")
    asset = provider.lookup_lyrics("Fast Car", "Tracy Chapman", metadata)
    assert asset.found is True
    assert asset.source == "musixmatch"
    assert asset.lyrics == "Fast car\nFast car"


def test_musicbrainz_provider_returns_metadata_summary() -> None:
    payloads = {
        "/recording?": {
            "recordings": [
                {
                    "id": "rec1",
                    "title": "Fast Car",
                    "score": "100",
                    "artist-credit": [{"name": "Tracy Chapman"}],
                }
            ]
        },
        "/recording/rec1": {
            "id": "rec1",
            "title": "Fast Car",
            "artist-credit": [{"name": "Tracy Chapman"}],
            "length": "300000",
            "first-release-date": "1988-04-06",
            "genres": [{"name": "folk rock", "count": 3}],
            "tags": [{"name": "folk", "count": 2}],
            "relations": [
                {"work": {"id": "work1"}},
                {"type": "producer", "artist": {"name": "David Kershenbaum"}},
            ],
            "releases": [{"id": "rel1", "title": "Tracy Chapman", "date": "1988-04-06"}],
        },
        "/release/rel1": {
            "id": "rel1",
            "title": "Tracy Chapman",
            "date": "1988-04-06",
            "status": "Official",
            "country": "US",
            "label-info": [{"label": {"name": "Elektra"}}],
            "genres": [{"name": "singer-songwriter", "count": 1}],
            "relations": [{"type": "producer", "artist": {"name": "David Kershenbaum"}}],
        },
        "/work/work1": {
            "id": "work1",
            "title": "Fast Car",
            "type": "Song",
            "genres": [],
            "tags": [],
            "relations": [
                {"type": "writer", "artist": {"name": "Tracy Chapman"}},
                {"type": "lyricist", "artist": {"name": "Tracy Chapman"}},
                {"type": "composer", "artist": {"name": "Tracy Chapman"}},
            ],
        },
    }
    provider = MusicBrainzMetadataProvider(http_client=FakeHttpClient(payloads), cache_store=None)
    metadata = provider.lookup_metadata("Fast Car", "Tracy Chapman")
    assert metadata.matched is True
    assert metadata.writer_count == 1
    assert metadata.producer_count == 1
    assert metadata.labels == ["Elektra"]
    assert "folk rock" in metadata.genres


def test_musicbrainz_provider_handles_no_matches() -> None:
    provider = MusicBrainzMetadataProvider(http_client=FakeHttpClient({"/recording?": {"recordings": []}}), cache_store=None)
    metadata = provider.lookup_metadata("Unknown", "Nobody")
    assert metadata.matched is False
