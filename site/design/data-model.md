# Data Model

The central aggregate is `SongRecord`.

`SongRecord` contains:

- original query fields
- matched title and artist
- chart summary fields
- metadata enrichment fields
- optional lyric asset
- optional lyric feature set
- provenance entries
- recoverable errors

Supporting entities:

- `ChartSummary`
- `MetadataSummary`
- `LyricAsset`
- `LyricFeatureSet`
- `ScoreCard`
- `ProvenanceEntry`
- `CorpusEntry`

These types are defined in `study_system.domain.models`.
