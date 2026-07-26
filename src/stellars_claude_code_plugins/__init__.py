"""Stellars Claude Code Plugins - shared orchestration engine."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    # Single-source the version from package metadata (pyproject.toml is the
    # source of truth). A hard-coded literal here silently drifts - it sat at
    # 0.8.43 while the project shipped 1.6.31.
    __version__ = _version("stellars-claude-code-plugins")
except PackageNotFoundError:  # running from a source tree with no install
    __version__ = "0.0.0"
