# Implementation Plan

**Project:** Music Study Data Collection and Scoring System  
**Companion documents:** [Music-Study-Design.md](./Music-Study-Design.md), [study-design-srs.md](./study-design-srs.md)  
**Implementation language:** Python  
**Status:** Draft v0.1

## Goal

This plan translates the software requirements in `study-design-srs.md` into an implementation sequence for a production-quality Python system. The target outcome is a layered, testable, documented research application with clear contract boundaries, modern packaging via `pyproject.toml`, MkDocs Material documentation, Mermaid diagrams, structured logging, Sphinx-compliant docstrings, and full unit-test coverage for core logic.

## Current Repo Review

The current repository is a mixed R and Python data project. Relative to the SRS, the current Python surface is still at prototype stage:

| Area | Current state | Gap against SRS |
|---|---|---|
| Python implementation | One script: `song_study_lookup.py` | Must be split into layered package modules |
| Packaging | No `pyproject.toml` | Must add Python project metadata, dependencies, tooling, and coverage config |
| Virtual environment | No repo-standard `.venv` workflow defined | Must standardize environment creation and activation in docs |
| Tests | No `tests/` package | Must add unit, integration, fixture, and coverage workflow |
| Coverage tooling | `coverage` not installed; no `pytest-cov` config | Must add measurable coverage reporting |
| Docs site | Existing R-generated `docs/` output only | Must add `mkdocs.yml`, Material theme, API docs, design docs, context docs |
| API docs | None for Python | Must add docstring-driven API reference |
| Logging | No structured logging framework in prototype | Must add logging policy, logger factory, and execution tracing |
| Contract boundaries | Logic, I/O, HTTP, and formatting are in one file | Must separate interfaces, application, domain, and infrastructure layers |
| Study workflow | No batch corpus pipeline or blind scoring workflow | Must implement corpus, enrichment, scoring, and export pipelines |

## Architecture Direction

The implementation should use a `src/` layout and explicit layer boundaries:

```text
rwd-billboard-data/
  pyproject.toml
  README.md
  mkdocs.yml
  site/
    index.md
    context.md
    design/
      architecture.md
      data-model.md
      diagrams.md
    api/
      index.md
  docs/
    ... generated MkDocs output ...
  src/
    study_system/
      interfaces/
      application/
      domain/
      infrastructure/
      config/
  tests/
    unit/
    integration/
    fixtures/
```

## Design Patterns to Use

| Pattern | Planned usage |
|---|---|
| **Repository** | Persistence boundary for song records, provenance, scoring records, and caches |
| **Adapter** | Provider integrations for chart data, metadata providers, and lyrics providers |
| **Strategy** | Swappable match scoring, lyric feature extraction, and scoring packet formatting |
| **Factory** | Provider assembly and configuration-based service creation |
| **Service Layer** | Application orchestration for corpus build, enrichment, scoring, and export |
| **DTO / Mapper** | Stable transfer models between layers and export formats |
| **Command** | CLI subcommands such as `lookup`, `build-corpus`, `enrich`, `score`, and `export` |

## Coding Standards

- Use type hints throughout.
- Use `src/` layout for import discipline.
- Use Sphinx-compliant docstrings in reStructuredText style for all public modules, classes, and functions.
- Use the standard `logging` package with structured context fields and centralized logger configuration.
- Use dataclasses or validated models for immutable or semi-immutable domain objects.
- Keep domain logic free of HTTP, filesystem, and CLI concerns.

## Implementation Table

| Phase | Workstream | Deliverables | Patterns / boundaries | Tests and coverage target | Docs and tooling |
|---|---|---|---|---|---|
| `P0` | Project bootstrap | `pyproject.toml`, `src/` layout, `.venv` instructions in `README.md`, base package, lint/test config | Establish contract boundaries between `interfaces`, `application`, `domain`, and `infrastructure` | Add `pytest`, `pytest-cov`, `coverage`; baseline smoke tests; target `>= 40%` on new package shell | Add MkDocs Material, `mkdocs.yml`, landing page, project context page |
| `P1` | Domain foundation | `models.py`, `scoring.py`, `feature_rules.py`, `provider_types.py` | Domain layer owns entities, SCI rules, feature models, and invariants; no provider code allowed | Full unit tests for rubric math, validation, normalization, and feature extraction; target `>= 85%` in `domain/` | API docs for domain models; design notes for data model |
| `P2` | Infrastructure contracts | provider interfaces, repository interfaces, HTTP client, retry/rate-limit helpers, cache abstraction | Adapter + Repository patterns; infrastructure may depend on domain contracts but not on CLI | Unit tests for adapters using fixtures; target `>= 80%` in `infrastructure/` excluding live network | Architecture doc for provider boundaries and provenance |
| `P3` | Application services | `corpus_service.py`, `enrichment_service.py`, `scoring_service.py`, `export_service.py`, DTOs | Service Layer coordinates workflows; application depends on interfaces, not concrete providers | Unit and fixture-driven integration tests; target `>= 85%` in `application/` | Sequence diagrams and workflow docs |
| `P4` | Chart and metadata adapters | local Billboard chart adapter, MusicBrainz adapter, lyrics adapter, provider registry | Adapter pattern with confidence scoring and explicit provenance mapping | Contract tests with recorded payloads; target `>= 80%` for adapter code | Provider capability matrix and legal notes |
| `P5` | Corpus and batch pipeline | corpus import, batch enrichment, checkpointing, resumable jobs, error reporting | Repository + Service Layer; batch pipeline separated from single-song CLI | Integration tests for batch success, partial failure, and resume; target `>= 75%` end-to-end workflow coverage | Ops doc for running pilot / expanded / full study phases |
| `P6` | Blind scoring workflow | scoring packet export, score import, SCI aggregation, inter-rater comparison | Strategy for packet formatting and scorer inputs; domain remains scorer-agnostic | Unit tests for redaction and SCI aggregation; target `>= 90%` in scoring components | Study workflow doc and scoring rubric usage guide |
| `P7` | Export and reporting | flat CSV export, rich JSON export, provenance export, summary report CLI | DTO + Mapper patterns; export layer cannot call providers directly | Export schema tests and regression snapshots; target `>= 85%` in export code | Dataset schema reference and analysis handoff docs |
| `P8` | Logging and observability | centralized logger config, structured logs, run summary metrics, failure tracing | Cross-cutting concern isolated in config and infrastructure utility modules | Tests for logger config and failure-path instrumentation; target `>= 70%` in logging helpers | Troubleshooting page and operational examples |
| `P9` | Documentation completion | API docs, architecture docs, context docs, design docs, Mermaid diagrams, developer guide | Documentation mirrors layer boundaries and use cases | Documentation build validation in CI | MkDocs Material site with Mermaid support and API reference |
| `P10` | Quality gates and release readiness | CI workflow, coverage gates, test matrix, versioning, release checklist | Enforce package-level contracts and regression safety | Repository-wide target `>= 85%` unit coverage for Python package, `>= 70%` integration coverage for workflows | Release checklist, contribution guide, maintenance notes |

## Layer Contracts

| Layer | Responsibilities | May depend on | Must not depend on |
|---|---|---|---|
| `interfaces` | CLI parsing, command dispatch, output formatting | `application`, `config` | concrete provider internals |
| `application` | workflow orchestration, DTO assembly, use-case coordination | `domain`, abstract repositories, abstract providers | CLI implementation details, raw HTTP |
| `domain` | entities, scoring rules, feature rules, validation | Python standard library and small validation helpers | HTTP, filesystem, CLI, provider SDKs |
| `infrastructure` | HTTP clients, file persistence, cache, provider adapters | `domain`, `application` abstractions | CLI concerns, study-specific scoring policy |
| `config` | settings, logger setup, provider wiring | all layers as needed for assembly only | domain rules |
| `tests` | verification and fixtures | all layers | production side effects outside test control |

## Planned Tooling

| Category | Planned tool |
|---|---|
| Packaging | `pyproject.toml` with `setuptools` or `hatchling` |
| Virtual environment | local `.venv` documented in `README.md` |
| Testing | `pytest` |
| Coverage | `pytest-cov` and `coverage[toml]` |
| Documentation site | `mkdocs`, `mkdocs-material`, `mkdocstrings[python]` |
| Mermaid support | `pymdown-extensions` or Material Mermaid integration |
| Typing and quality | `mypy`, `ruff`, `black` or `ruff format` |
| HTTP | `httpx` or standard library adapter wrapper |
| Model validation | `dataclasses` or `pydantic` depending on complexity |

## Documentation Plan

| Doc | Purpose |
|---|---|
| `README.md` | environment setup, quickstart, CLI overview, study context |
| `site/index.md` | project overview and navigation hub |
| `site/context.md` | research context and study framing |
| `site/design/architecture.md` | layer boundaries and component responsibilities |
| `site/design/data-model.md` | entities, provenance, exports, and scoring structures |
| `site/design/diagrams.md` | Mermaid system, sequence, state, and data diagrams |
| `site/api/` | generated Python API documentation from docstrings |
| `site/usage/` | batch runs, scoring workflow, export workflow |
| `docs/` | generated publishable MkDocs site output |

## Testing and Coverage Plan

| Scope | Requirement |
|---|---|
| Unit tests | Required for all domain logic, services, adapters, and export mappers |
| Integration tests | Required for corpus build, enrichment, scoring, and export workflows using fixtures |
| Fixture policy | No live-network dependency in default test suite |
| Coverage command | `pytest --cov=study_system --cov-report=term-missing --cov-report=xml --cov-report=html` |
| Coverage threshold | Phase targets in table above; final repository target `>= 85%` Python unit coverage |
| Reporting | Coverage summary in CI and checked into release review notes |

## Baseline Coverage Report

Current Python coverage status for this repository is effectively **unmeasured and functionally zero for the planned package**, because:

| Metric | Current state |
|---|---|
| Python source files in scope | `1` prototype file: `song_study_lookup.py` |
| Python tests present | `0` |
| `coverage` installed in current environment | `No` |
| `pytest` available | `Yes` |
| Measurable package coverage | `Not currently reportable` |
| Practical baseline against target system | `0% of planned tested package surface` |

This means the first implementation milestone should establish coverage tooling before meaningful code-coverage reporting is expected.

## Recommended File and Module Plan

| Path | Purpose |
|---|---|
| `pyproject.toml` | dependency, build, tooling, and coverage configuration |
| `src/study_system/domain/models.py` | song, lyric, feature, provenance, and score entities |
| `src/study_system/domain/scoring.py` | SCI computation and subscore validation |
| `src/study_system/domain/feature_rules.py` | normalization and lyric feature extraction logic |
| `src/study_system/application/services/enrichment_service.py` | orchestration of matching, provider enrichment, and feature extraction |
| `src/study_system/infrastructure/providers/chart_source.py` | local Billboard chart adapter |
| `src/study_system/infrastructure/providers/musicbrainz_provider.py` | MusicBrainz adapter |
| `src/study_system/infrastructure/providers/lyrics_provider.py` | lyrics provider adapter and policy hooks |
| `src/study_system/interfaces/cli.py` | top-level CLI entrypoint |
| `tests/unit/` | fast tests for domain, service, and mapper logic |
| `tests/integration/` | fixture-backed workflow tests |
| `mkdocs.yml` | Material documentation site configuration |

## Exit Criteria

The implementation plan should be considered complete when:

- the package is installable from `pyproject.toml`
- the `.venv` workflow is documented in `README.md`
- the Python system is layered with enforceable contract boundaries
- public APIs have Sphinx-compliant docstrings
- structured logging is available in batch and CLI workflows
- MkDocs Material builds a site containing context, design, diagrams, usage, and API docs
- CI reports coverage and enforces thresholds
- the pilot study workflow can run end-to-end with tests and reproducible exports
