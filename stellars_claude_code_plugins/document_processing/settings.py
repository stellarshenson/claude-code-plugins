"""User settings for document-processing plugin.

Settings live in ``.stellars-plugins/settings.json`` next to ``.claude/``. When
the file does not exist the first CLI invocation that needs a setting calls
:func:`prompt_first_run` (or the caller may pre-seed via :func:`save`).

Project-local takes precedence over home:

    1. ``./.stellars-plugins/settings.json`` (project root, cwd-rooted)
    2. ``~/.stellars-plugins/settings.json``

Keys (all optional; defaults applied on read):

    - ``semantic_enabled`` (bool, default False) — allow semantic grounding
      (ModernBERT + FAISS). Costs model download on first use (~50-150 MB)
      and runtime CPU/GPU inference. Opt-in.
    - ``semantic_model`` (str) — HF model id. Default
      ``jhu-clsp/mmBERT-small`` (smallest mmBERT).
    - ``semantic_device`` (str) — ``"auto"`` / ``"cpu"`` / ``"cuda"``.
      ``"auto"`` picks cuda when available else cpu.
    - ``cache_dir`` (str) — parquet cache for chunks + embeddings. Default
      ``./.stellars-plugins/cache``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys

SETTINGS_DIR_NAME = ".stellars-plugins"
SETTINGS_FILE_NAME = "settings.json"


@dataclass
class Settings:
    semantic_enabled: bool = False
    semantic_model: str = "intfloat/multilingual-e5-small"
    semantic_device: str = "auto"
    cache_dir: str = ""  # resolved on load


def _project_root() -> Path:
    """Return the nearest ancestor containing a ``.claude`` directory, else cwd."""
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / ".claude").is_dir():
            return p
    return cwd


def _candidate_paths() -> list[Path]:
    """Ordered list of settings file paths to probe."""
    project = _project_root() / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME
    home = Path.home() / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME
    return [project, home]


def settings_path(prefer: str = "project") -> Path:
    """Return the preferred settings file path (for writes).

    ``prefer`` is ``"project"`` (default) or ``"home"``.
    """
    if prefer == "home":
        return Path.home() / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME
    return _project_root() / SETTINGS_DIR_NAME / SETTINGS_FILE_NAME


def load() -> Settings:
    """Load settings. Falls back to defaults for missing file or keys."""
    for path in _candidate_paths():
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            s = Settings(**{k: v for k, v in raw.items() if k in Settings.__annotations__})
            if not s.cache_dir:
                s.cache_dir = str(path.parent / "cache")
            return s
    # No settings file — return defaults pointing at project-local cache
    default_base = _project_root() / SETTINGS_DIR_NAME
    return Settings(cache_dir=str(default_base / "cache"))


def save(settings: Settings, *, prefer: str = "project") -> Path:
    """Write settings to disk. Returns the path written."""
    path = settings_path(prefer)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    # Don't persist auto-computed cache_dir if it's the default
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def settings_exist() -> bool:
    return any(p.is_file() for p in _candidate_paths())


def prompt_first_run(*, stream=sys.stderr, input_fn=input) -> Settings:
    """Interactively ask the user whether to enable semantic grounding.

    Writes the answer to the project-local settings file. Returns the
    resulting Settings. Non-interactive environments (``--no-input``,
    missing stdin) get defaults (semantic disabled) without prompting.
    """
    if not sys.stdin.isatty():
        s = Settings()
        s.cache_dir = str(_project_root() / SETTINGS_DIR_NAME / "cache")
        save(s)
        return s

    print(
        "stellars-claude-code-plugins: semantic grounding setup\n"
        "=======================================================\n"
        "Optional: enable ModernBERT + FAISS semantic grounding for\n"
        "document-processing? This adds a 4th grounding layer that finds\n"
        "passages by meaning even when wording and terms differ.\n"
        "\n"
        "Costs:\n"
        "  - First use downloads ~150 MB model (jhu-clsp/mmBERT-small)\n"
        "  - Requires: pip install stellars-claude-code-plugins[semantic]\n"
        "  - Runtime: CPU or GPU inference per claim\n"
        "\n"
        "Benefit: saves tokens - agent gets the right passage directly.\n",
        file=stream,
    )
    ans = input_fn("Enable semantic grounding? [y/N]: ").strip().lower()
    enabled = ans in ("y", "yes")

    s = Settings(semantic_enabled=enabled)
    s.cache_dir = str(_project_root() / SETTINGS_DIR_NAME / "cache")
    path = save(s)
    print(f"Saved settings → {path}", file=stream)
    return s


def ensure_loaded(*, auto_prompt: bool = True) -> Settings:
    """Load settings; if none exist and ``auto_prompt`` is True, run the prompt."""
    if settings_exist():
        return load()
    if auto_prompt:
        return prompt_first_run()
    return load()


def is_semantic_available() -> bool:
    """Check if the semantic-grounding optional deps are importable."""
    for mod in ("torch", "transformers", "faiss", "pyarrow"):
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def semantic_install_hint() -> str:
    return (
        "Semantic grounding requires optional dependencies. Install with:\n"
        "  pip install 'stellars-claude-code-plugins[semantic]'\n"
        "or individually:\n"
        "  pip install torch transformers faiss-cpu pyarrow\n"
    )


# Suppress environment-based override for tests via STELLARS_SETTINGS_HOME
def _env_override() -> Path | None:
    val = os.environ.get("STELLARS_SETTINGS_HOME")
    return Path(val) if val else None
