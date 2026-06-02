"""User settings for document-processing plugin.

Settings live in ``.stellars-plugins/settings.json`` next to ``.claude/``. When
the file does not exist the first CLI invocation that needs a setting calls
:func:`prompt_first_run` (or the caller may pre-seed via :func:`save`).

Project-local takes precedence over home:

    1. ``./.stellars-plugins/settings.json`` (project root, cwd-rooted)
    2. ``~/.stellars-plugins/settings.json``

Whether semantic grounding runs is NOT a persisted setting - it is a per-call
flag on the grounder, controlled by ``--semantic`` (default off). The
settings file only holds the semantic *model configuration* used when that flag
turns the layer on. An old file that still carries a ``semantic_enabled`` key is
loaded harmlessly: unknown keys are filtered out on read.

Keys (all optional; defaults applied on read):

    - ``semantic_model`` (str) — HF model id with a pre-exported
      ``onnx/model.onnx``. Default ``intfloat/multilingual-e5-small``.
    - ``semantic_device`` (str) — accepted for backward compatibility; the
      ONNX Runtime path runs on CPU regardless of value.
    - ``cache_dir`` (str) — parquet cache for chunks + embeddings. Default
      ``./.stellars-plugins/cache``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys

SETTINGS_DIR_NAME = ".stellars-plugins"
SETTINGS_FILE_NAME = "settings.json"


@dataclass
class Settings:
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
    """Write a default settings file (model + cache config) and return it.

    Semantic grounding is no longer a persisted on/off setting - it is enabled
    per call via ``--semantic`` (which also brings the NLI entailment layer
    online). So there is nothing to ask: this just seeds the model/cache config
    and notes how to turn the layer on. ``input_fn`` is retained for signature
    compatibility but unused.
    """
    s = Settings()
    s.cache_dir = str(_project_root() / SETTINGS_DIR_NAME / "cache")
    path = save(s)
    print(
        f"Saved settings → {path}\n"
        "Semantic grounding (+ NLI entailment) is opt-in per call: pass "
        "'--semantic' to any grounding command. Requires the optional "
        "extras:\n" + semantic_install_hint(),
        file=stream,
    )
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
    for mod in ("onnxruntime", "transformers", "faiss", "pyarrow", "huggingface_hub"):
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
        "  pip install onnxruntime transformers faiss-cpu pyarrow huggingface_hub\n"
    )
