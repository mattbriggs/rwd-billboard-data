# rwd-billboard-data

This repository contains two related systems:

- a historical Billboard chart archive built from the existing R notebooks and scripts
- a packaged Python study system for song-level corpus building, enrichment, lyric feature extraction, blind scoring workflows, and export

The Python system was added to support the research design in [design/Music-Study-Design.md](design/Music-Study-Design.md) and the software architecture in [design/study-design-srs.md](design/study-design-srs.md).

## Python Study System

The Python package lives under `src/study_system/` and is organized into explicit layers:

- `interfaces`: CLI commands and output surfaces
- `application`: use-case orchestration services
- `domain`: scoring rules, entities, normalization, and lyric features
- `infrastructure`: chart adapters, provider adapters, caching, and persistence
- `tests`: unit and integration coverage

### Quickstart

Use a virtual environment for this project. It is not technically required, but it is the recommended setup because the repo installs project-specific CLI, test, and documentation dependencies like `pytest`, `mkdocs`, and `mkdocstrings`.

Check that you are using Python `3.12+`:

```bash
python3 --version
```

Create and activate a local virtual environment on macOS or Linux:

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

The quotes around `.[test,docs]` matter in `zsh`, which otherwise treats the brackets as a glob pattern.

When the environment is active, `python`, `pip`, `pytest`, `mkdocs`, and `song-study` will resolve from `.venv/` instead of your system Python.

Optional: if you have a licensed Musixmatch API key, set it before running enrichment to add a higher-coverage lyrics fallback provider:

```bash
export MUSIXMATCH_API_KEY="your-key-here"
```

Leave the environment with:

```bash
deactivate
```

Run the test suite:

```bash
pytest
```

Run a single-song lookup:

```bash
song-study lookup --title "Fast Car" --artist "Tracy Chapman" --pretty
```

Or use the compatibility wrapper:

```bash
python3 song_study_lookup.py --title "Fast Car" --artist "Tracy Chapman" --pretty
```

### CLI Workflows

Build a pilot corpus from weekly peak chart performance:

```bash
song-study build-corpus --years 1965 1975 1985 1995 2005 2015 --top-n 25 --output outputs/pilot-corpus.json
```

The default `build-corpus` strategy is now `stratified_peak`, which reduces the over-representation of `#1` hits by sampling across peak-rank bands. Use `--selection-strategy peak_top_n` if you want the older behavior that simply takes the best weekly peaks.

Enrich a corpus:

```bash
song-study enrich --corpus-file outputs/pilot-corpus.json --output outputs/enriched-records.json
```

`enrich` now stores full lyrics by default for local research runs. Use `--omit-lyrics` if you want metadata-and-features only.

Lyric lookup now tries stronger title and artist normalization first, then uses a provider chain. Out of the box it uses `Lyrics.ovh`, and if `MUSIXMATCH_API_KEY` is set it will try Musixmatch as an additional fallback provider.

Export blind scoring packets:

```bash
song-study score-packets --records-file outputs/enriched-records.json --output outputs/scoring-packets.json
```

This writes a scoring template that retains the enriched record context by default, including `lyrics_text` when available. Each packet also includes the five rubric fields with `null` placeholders plus optional `scorer_id` and `notes`. Use `--blind` if you want a reduced blind-scoring view, or `--omit-lyrics` if you want packets without lyric text.

Export a final dataset after scores have been collected:

```bash
song-study export-dataset --records-file outputs/enriched-records.json --scores-file outputs/scores.json --output outputs/final-dataset.csv
```

By default, `export-dataset` keeps manual scores when present, skips incomplete scoring packets with a warning, and generates deterministic fallback heuristic scores for lyric-bearing songs that still lack a completed manual score. The final CSV marks each row with `score_source` so you can distinguish `manual`, `auto_heuristic`, and `missing`. Add `--strict-scores` if you want the command to fail on any incomplete score entry.

## Documentation

The project includes MkDocs Material configuration and Mermaid diagram support.
The authored documentation source lives in `site/`, and the publishable generated site is written to `docs/`.

Serve the documentation locally:

```bash
mkdocs serve
```

Run the docs commands from the active virtual environment so `mkdocs-material` and `mkdocstrings` come from the project install.

The documentation site includes:

- project context
- implementation and architecture notes
- Mermaid system and workflow diagrams
- usage guides
- API documentation driven by Sphinx-compliant docstrings

## Historical Billboard Archive

The original chart archive remains available in this repository.

Files of interest:

- `data-out/hot-100-current.csv` contains weekly Billboard Hot 100 data back to 1958
- `data-out/billboard-200-current.csv` contains weekly Billboard 200 data back to 1967

The R and notebook workflows remain in place for chart scraping, archive combination, and exploratory maintenance:

- `01-scrape-charts.Rmd`
- `02-combine-charts.Rmd`
- `03-assignment-data.Rmd`
- `03-check-charts.Rmd`
- `notebooks/`

## Notes and Constraints

- `lookup` omits full lyric text unless `--include-lyrics` is requested.
- `enrich` is optimized for private bulk analysis and persists `lyrics_text` by default unless `--omit-lyrics` is used.
- The current chart-based corpus builder uses the local weekly archive, not Billboard year-end rankings.
- Open metadata providers can be incomplete for producers, labels, samples, and interpolation relationships, so audit workflows are still important for serious study use.
