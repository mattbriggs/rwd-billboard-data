# Music Study System

This documentation describes the packaged Python system that supports the song study defined in the repository's `design/Music-Study-Design.md`.

The system turns the original single-file lookup prototype into a structured research application with:

- layered package boundaries
- chart corpus building
- metadata and lyric enrichment
- blind scoring packet generation
- dataset exports
- logging, tests, and packaging

Use the pages in this site for setup, architecture, Mermaid diagrams, and generated API reference.

The recommended workflow uses a local virtual environment in `.venv/` so the CLI, test tools, and MkDocs dependencies stay isolated to this repository.
