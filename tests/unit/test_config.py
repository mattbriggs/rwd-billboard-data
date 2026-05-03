"""Unit tests for configuration helpers."""

from __future__ import annotations

from pathlib import Path

from study_system.config.logging_config import configure_logging
from study_system.config.settings import discover_settings


def test_discover_settings_uses_project_root() -> None:
    root = Path("/tmp/example")
    settings = discover_settings(root)
    assert settings.project_root == root
    assert settings.default_billboard_file == root / "data-out" / "hot-100-current.csv"
    assert settings.musixmatch_api_key is None


def test_discover_settings_reads_musixmatch_api_key(monkeypatch) -> None:
    monkeypatch.setenv("MUSIXMATCH_API_KEY", "test-key")
    settings = discover_settings(Path("/tmp/example"))
    assert settings.musixmatch_api_key == "test-key"


def test_configure_logging_runs_without_error() -> None:
    configure_logging(verbose=True)
