"""Orchestration engine for Claude Code plugins.

YAML-driven phase lifecycle management with FSM transitions,
gate validation, and multi-agent orchestration.
"""

from stellars_claude_code_plugins.autobuild.fsm import (
    FSM,
    build_phase_lifecycle_fsm,
)
from stellars_claude_code_plugins.autobuild.model import (
    Model,
    load_model,
    resolve_phase_key,
    validate_model,
)
from stellars_claude_code_plugins.autobuild.orchestrator import main

__all__ = [
    "FSM",
    "Model",
    "build_phase_lifecycle_fsm",
    "load_model",
    "main",
    "resolve_phase_key",
    "validate_model",
]
