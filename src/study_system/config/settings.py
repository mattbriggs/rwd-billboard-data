"""Application settings helpers.

:mod:`study_system.config.settings` centralizes filesystem defaults so the rest
of the application can avoid hard-coded paths.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    """Resolved application settings.

    :param project_root: Repository root path.
    :param default_billboard_file: Default weekly Hot 100 archive.
    :param cache_dir: Directory for cached provider responses.
    :param output_dir: Directory for generated JSON and CSV exports.
    :param musixmatch_api_key: Optional Musixmatch API key.
    """

    project_root: Path
    default_billboard_file: Path
    cache_dir: Path
    output_dir: Path
    musixmatch_api_key: str | None = None


def discover_settings(project_root: Path | None = None) -> AppSettings:
    """Create application settings from repository defaults.

    :param project_root: Optional explicit repository root.
    :returns: Resolved settings instance.
    """

    root = project_root or Path(__file__).resolve().parents[3]
    return AppSettings(
        project_root=root,
        default_billboard_file=root / "data-out" / "hot-100-current.csv",
        cache_dir=root / ".cache" / "study_system",
        output_dir=root / "outputs",
        musixmatch_api_key=os.environ.get("MUSIXMATCH_API_KEY"),
    )
