# Architecture

The implementation follows a layered design with clear contract boundaries.

## Layers

- `interfaces`: command-line entrypoints and command parsing
- `application`: use-case orchestration for lookup, corpus building, scoring, and export
- `domain`: normalization, matching, scoring rules, and immutable data structures
- `infrastructure`: provider adapters, local chart access, filesystem persistence, cache, and HTTP utilities

## Key Patterns

- **Repository** for persisted song and score datasets
- **Adapter** for chart, metadata, and lyrics providers
- **Service Layer** for orchestration of study workflows
- **Strategy** for scoring packets and future matching or feature variants
- **Command** for CLI subcommands

## Contract Boundaries

- Domain code must not know about HTTP, CSV files, or CLI parsing.
- Application services depend on provider and repository contracts, not direct provider implementations.
- Infrastructure implements those contracts and may depend on the standard library plus local file layout.
