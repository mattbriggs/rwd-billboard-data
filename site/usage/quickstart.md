# Quickstart

## Environment

Use a virtual environment for this repo. The package itself is small, but the test and docs extras install project-specific tooling and are best kept out of your system Python.

Confirm you have Python `3.12+`:

```bash
python3 --version
```

Create and activate a local environment on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,docs]'
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test,docs]"
```

The quotes around `.[test,docs]` are important in `zsh`, which otherwise expands the brackets before `pip` runs.

Optional: if you have a licensed Musixmatch API key, export it before running enrichment so the lyrics provider chain can use it as a fallback:

```bash
export MUSIXMATCH_API_KEY="your-key-here"
```

When you are done, leave the environment with `deactivate`.

## Single Song Lookup

```bash
song-study lookup --title "Fast Car" --artist "Tracy Chapman" --pretty
```

## Build a Corpus

```bash
song-study build-corpus --years 1965 1975 1985 1995 2005 2015 --top-n 25 --output outputs/pilot-corpus.json
```

The default selection strategy is `stratified_peak`, which samples across peak-rank bands so your corpus is less dominated by `#1` hits. Use `--selection-strategy peak_top_n` if you want the older pure peak-rank sort.

## Enrich a Corpus

```bash
song-study enrich --corpus-file outputs/pilot-corpus.json --output outputs/enriched-records.json
```

This command keeps `lyrics_text` in saved records by default for local analysis. Add `--omit-lyrics` to suppress lyric persistence.

Lyric lookup uses stronger title and artist normalization and a provider chain. By default it uses `Lyrics.ovh`; if `MUSIXMATCH_API_KEY` is set it will also try Musixmatch.

## Export Blind Scoring Packets

```bash
song-study score-packets --records-file outputs/enriched-records.json --output outputs/scoring-packets.json
```

This creates a scoring template that keeps the enriched record context by default, including `lyrics_text` when available, and adds the five rubric fields as `null` placeholders. Use `--blind` for a reduced blind-scoring packet, and `--omit-lyrics` if you want packets without lyric text.

## Export Final Dataset

```bash
song-study export-dataset --records-file outputs/enriched-records.json --scores-file outputs/scores.json --output outputs/final-dataset.csv
```

By default, this command keeps manual scores when present, skips incomplete scoring packets with a warning, and generates fallback heuristic scores for lyric-bearing songs that still lack a completed manual score. The output includes `score_source` so you can distinguish `manual`, `auto_heuristic`, and `missing`. Add `--strict-scores` if you want incomplete packets to stop the export.
