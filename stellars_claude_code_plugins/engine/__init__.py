"""Orchestration engine for Claude Code plugins.

YAML-driven phase lifecycle management with FSM transitions,
gate validation, and multi-agent orchestration.
"""

from stellars_claude_code_plugins.engine.fsm import (
    Event,
    FSM,
    FSMConfig,
    State,
    Transition,
    build_phase_lifecycle_fsm,
    resolve_phase_key,
)
from stellars_claude_code_plugins.engine.model import (
    Model,
    load_model,
    validate_model,
)
from stellars_claude_code_plugins.engine.orchestrator import main

__all__ = [
    "Event",
    "FSM",
    "FSMConfig",
    "Model",
    "State",
    "Transition",
    "build_phase_lifecycle_fsm",
    "load_model",
    "main",
    "resolve_phase_key",
    "validate_model",
]
