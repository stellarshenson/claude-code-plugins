#!/usr/bin/env python3
"""YAML-driven declarative build iteration orchestrator.

All content loaded from YAML resources (phases, agents, workflow types,
guardian checklist, display strings). The engine is content-agnostic -
each plugin provides its own YAML resource files.

10-command CLI with 2 calls per phase (start + end).
Stateful phases, agent review, automated testing, independent gatekeeper.

State: <artifacts_dir>/state.yaml
Audit: <artifacts_dir>/log.yaml
Failures: <artifacts_dir>/failures.yaml
"""

import argparse
import collections
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import tiktoken
import yaml

from stellars_claude_code_plugins.engine.fsm import (
    ADVANCE,
    END,
    GATE_FAIL,
    GATE_PASS,
    PENDING,
    READBACK_FAIL,
    READBACK_PASS,
    REJECT,
    SKIP,
    START,
    build_phase_lifecycle_fsm,
)
from stellars_claude_code_plugins.engine.fsm import (
    ALL_STATES as _FSM_ALL_STATES,
)
from stellars_claude_code_plugins.engine.model import (
    _KNOWN_VARS as _KNOWN_TEMPLATE_VARS,
)
from stellars_claude_code_plugins.engine.model import (
    load_model,
    resolve_phase_key,
    validate_model,
)

# ── Module-level state (set by _initialize) ────────────────────────

PROJECT_ROOT = Path.cwd()

_MODEL = None
DEFAULT_ARTIFACTS_DIR = None
STATE_FILE = None
LOG_FILE = None
FAILURES_FILE = None
CONTEXT_FILE = None
CMD = None
_SEP_CHAR = None
_SEP_WIDTH = None
_HDR_CHAR = None
_HDR_WIDTH = None
_PHASE_FSM = None
_FSM_STATE_VALUES = None
ITERATION_TYPES = {}
_CLI_TO_FQN = {}  # cli_name -> FQN workflow key (e.g., "full" -> "WORKFLOW::FULL")
_DEFAULT_CLI_NAME = ""  # first independent workflow's cli_name
PHASE_AGENTS = {}
_PHASE_START = {}
_PHASE_END = {}

_AUTO_ACTION_REGISTRY = {}

_initialized = False


def _initialize(resources_dir: Path) -> None:
    """Load model from YAML resources and set up all module-level state.

    Called once by main() before any command handler runs. This defers
    model loading so the engine module can be imported without requiring
    a specific resources directory.
    """
    global _MODEL, DEFAULT_ARTIFACTS_DIR, STATE_FILE, LOG_FILE, FAILURES_FILE
    global CONTEXT_FILE, CMD, _SEP_CHAR, _SEP_WIDTH
    global _HDR_CHAR, _HDR_WIDTH, _PHASE_FSM, _FSM_STATE_VALUES
    global ITERATION_TYPES, _CLI_TO_FQN, _DEFAULT_CLI_NAME
    global PHASE_AGENTS, _PHASE_START, _PHASE_END
    global _AUTO_ACTION_REGISTRY, _initialized

    _MODEL = load_model(resources_dir)

    DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / _MODEL.app.artifacts_dir
    STATE_FILE = DEFAULT_ARTIFACTS_DIR / "state.yaml"
    LOG_FILE = DEFAULT_ARTIFACTS_DIR / "log.yaml"
    FAILURES_FILE = DEFAULT_ARTIFACTS_DIR / "failures.yaml"
    CONTEXT_FILE = DEFAULT_ARTIFACTS_DIR / "context.yaml"
    CMD = _MODEL.app.cmd or "python orchestrate.py"
    _SEP_CHAR = _MODEL.app.display.separator
    _SEP_WIDTH = _MODEL.app.display.separator_width
    _HDR_CHAR = _MODEL.app.display.header_char
    _HDR_WIDTH = _MODEL.app.display.header_width

    _PHASE_FSM = build_phase_lifecycle_fsm()
    _FSM_STATE_VALUES = set(_FSM_ALL_STATES)

    # Build ITERATION_TYPES keyed by cli_name, and cli_name -> FQN mapping
    ITERATION_TYPES.clear()
    _CLI_TO_FQN.clear()
    for fqn, wt in _MODEL.workflow_types.items():
        cli = wt.cli_name or fqn  # fallback to FQN if no cli_name
        _CLI_TO_FQN[cli] = fqn
        ITERATION_TYPES[cli] = {
            "description": wt.description,
            "phases": wt.phase_names,
            "required": wt.required,
            "skippable": wt.skippable,
        }
    # Derive default cli_name from first independent workflow
    _DEFAULT_CLI_NAME = ""
    for fqn, wt in _MODEL.workflow_types.items():
        if wt.independent and wt.cli_name:
            _DEFAULT_CLI_NAME = wt.cli_name
            break

    # Extract flat agent name lists from model.agents
    PHASE_AGENTS.clear()
    PHASE_AGENTS.update(
        {phase: [a.name for a in agents] for phase, agents in _MODEL.agents.items()}
    )

    # Populate _PHASE_START and _PHASE_END from model.phases
    _PHASE_START.clear()
    _PHASE_END.clear()
    for phase_name in _MODEL.phases:
        _PHASE_START[phase_name] = _make_phase_callable(phase_name, "start")
        _PHASE_END[phase_name] = _make_phase_callable(phase_name, "end")

    # Auto-action registry
    _AUTO_ACTION_REGISTRY.clear()
    _AUTO_ACTION_REGISTRY.update(
        {
            "plan_save": _action_plan_save,
            "iteration_summary": _action_iteration_summary,
            "iteration_advance": _action_iteration_advance,
        }
    )

    _initialized = True


# ── FSM helpers ─────────────────────────────────────────────────────


def _fire_fsm(event: str, state: dict) -> str:
    """Fire FSM event and sync phase_status to state dict.

    Syncs FSM from persisted state before firing, then writes back.
    All phase_status mutations go through this function.
    """
    status = state.get("phase_status", "pending")
    _PHASE_FSM.current_state = status if status in _FSM_STATE_VALUES else PENDING
    new_state = _PHASE_FSM.fire(event)
    state["phase_status"] = new_state
    return new_state


# ── Display helpers ─────────────────────────────────────────────────


def _msg(key: str, **kwargs) -> str:
    """Look up a message template from app.yaml and render with kwargs.

    This is the display text abstraction layer. All user-facing CLI output
    goes through this function, making the Python engine content-agnostic.
    Uses format_map with defaultdict(str) so missing variables render as
    empty strings instead of raising KeyError.
    """
    template = _MODEL.app.messages.get(key, key)
    ctx = {
        "cmd": CMD,
        "separator_line": _SEP_CHAR * _SEP_WIDTH,
        "header_line": _HDR_CHAR * _HDR_WIDTH,
    }
    ctx.update(kwargs)
    return template.format_map(collections.defaultdict(str, ctx))


def _cli(section: str, key: str) -> str:
    """Look up a CLI help string from app.yaml.

    Provides argparse descriptions and help text from YAML so CLI
    documentation can be customised without touching Python code.
    Supports top-level keys (description, epilog) and nested
    command/argument help via section.key lookup.
    """
    cli = _MODEL.app.cli
    if section == "description":
        return cli.description
    if section == "epilog":
        return cli.epilog.format_map(collections.defaultdict(str, {"cmd": CMD}))
    val = cli.commands.get(key, key) if section == "commands" else cli.args.get(key, key)
    return val.format_map(collections.defaultdict(str, {"cmd": CMD})) if "{" in val else val


# ── Exposed data structures ────────────────────────────────────────


def _guardian_checklist() -> str:
    """Return the guardian checklist text from model agents.

    Searches all phase agent definitions for the first guardian agent
    that has a checklist field. The checklist is injected into phase
    templates via the {{checklist}} template variable in _build_context().
    Used by guardian agents in both PLAN and REVIEW phases.
    """
    for agent_list in _MODEL.agents.values():
        for agent in agent_list:
            if agent.checklist:
                return agent.checklist
    return ""


def _current_workflow_type() -> str:
    """Get current workflow type (cli_name) from state."""
    state = _load_state()
    return (state or {}).get("type", _DEFAULT_CLI_NAME)


def _workflow_prefix(cli_name: str = "") -> str:
    """Get the workflow prefix from cli_name for phase resolution.

    Maps cli_name -> FQN -> prefix. E.g., "full" -> "WORKFLOW::FULL" -> "FULL".
    """
    cli = cli_name or _current_workflow_type()
    fqn = _CLI_TO_FQN.get(cli, cli)
    return fqn.split("::", 1)[1] if "::" in fqn else fqn


def _resolve_phase(phase: str) -> str:
    """Resolve a phase name to its namespaced key in phases.yaml."""
    return resolve_phase_key(_workflow_prefix(), phase, set(_MODEL.phases.keys()))


def _resolve_agents(phase: str) -> str:
    """Resolve a phase name to its namespaced key for agent lookup.

    Returns the resolved key if agents exist, or bare phase name if not.
    Not all phases have agents, so missing is not an error.
    """
    try:
        return resolve_phase_key(_workflow_prefix(), phase, set(_MODEL.agents.keys()))
    except KeyError:
        return phase  # phase has no agents defined - not an error


def _resolve_gate(phase: str, gate_type: str) -> str:
    """Resolve a gate key for a phase. Strict lookup, no fallback.

    Gate keys are namespaced: FULL::RESEARCH::readback, FULL::TEST::gatekeeper.
    Resolution: WORKFLOW::PHASE -> bare PHASE. Missing = KeyError.
    """
    gate_phases = {
        k.rsplit("::", 1)[0]
        for k in _MODEL.gates
        if "::" in k and k.rsplit("::", 1)[1] == gate_type
    }
    resolved = resolve_phase_key(_workflow_prefix(), phase, gate_phases)
    return f"{resolved}::{gate_type}"


def _resolve_lifecycle_gate(phase: str, lifecycle: str) -> str:
    """Resolve the gate key for a phase at a lifecycle point.

    Discovers the gate type from the model's lifecycle metadata instead of
    requiring a hardcoded gate name. For example, lifecycle='start' finds
    the gate type registered under on_start (e.g. 'readback'), then resolves
    the full namespaced key via _resolve_gate.

    Args:
        phase: phase name (e.g. 'RESEARCH', 'TEST')
        lifecycle: 'start' or 'end'
    """
    gate_types = {
        "start": _MODEL.start_gate_types,
        "end": _MODEL.end_gate_types,
    }.get(lifecycle, set())
    if not gate_types:
        return f"{phase}::{lifecycle}"
    # Use the first (typically only) gate type for this lifecycle point
    gate_type = next(iter(gate_types))
    return _resolve_gate(phase, gate_type)


def _build_agent_instructions(phase: str, ctx: dict | None = None) -> str:
    """Generate formatted agent instructions from model agents for a phase.

    Produces '### Agent N: DISPLAY_NAME' formatted text matching the
    pattern that v1 hardcoded in phase templates. If an agent has a
    checklist field, it is appended to the prompt. Template variables
    like {{checklist}} in agent prompts are resolved using the context dict.
    Called by _build_context() to populate the {{agents_instructions}} variable.
    """
    # Resolve namespaced agent key (FULL::RESEARCH, etc.) with fallback
    resolved = _resolve_agents(phase)
    agents = _MODEL.agents.get(resolved, [])
    if not agents:
        return ""

    lines = []
    for i, agent in enumerate(agents, start=1):
        prompt = agent.prompt
        checklist = agent.checklist or ""
        # Append checklist to prompt if agent has one
        if checklist:
            prompt = prompt.rstrip() + "\n\n" + checklist
        # Resolve any template variables in the prompt (e.g., {checklist})
        if ctx and "{" in prompt:
            prompt = prompt.format_map(collections.defaultdict(str, ctx))
        lines.append(f"### Agent {i}: {agent.display_name}")
        lines.append(prompt.rstrip())
        lines.append("")
    return "\n".join(lines).rstrip()


# ── Build context for template rendering ────────────────────────────


def _build_failures_context() -> str:
    """Build prior failures context string from failures.yaml."""
    all_failures = _load_failures()
    if not all_failures:
        return ""
    unsolved = {
        fid: f for fid, f in all_failures.items() if f.get("status") in {"new", "acknowledged"}
    }
    solved = {
        fid: f for fid, f in all_failures.items() if f.get("status") not in {"new", "acknowledged"}
    }
    parts = [f"\n**Prior failures** ({len(all_failures)} total, {len(unsolved)} unsolved):\n"]
    if unsolved:
        parts.append("Unsolved (investigation targets):\n")
        for fid, f in list(unsolved.items())[-5:]:
            parts.append(
                f"  - [{fid}] ({f.get('mode', '?')}) iter {f.get('iteration', '?')}: "
                f"{f.get('description', '?')}\n"
            )
    if solved:
        parts.append(f"Solved ({len(solved)}):\n")
        for fid, f in list(solved.items())[-3:]:
            parts.append(f"  - [{fid}] SOLVED: {f.get('solution', '?')}\n")
    return "".join(parts)


def _build_plan_context(state: dict) -> str:
    """Build iteration plan context string from state."""
    iteration_plan = state.get("iteration_plan", "")
    iteration = state.get("iteration", 1)
    if iteration_plan and iteration > 0:
        return f"\n**Iteration plan** (from planning iteration 0):\n{iteration_plan[:300]}\n"
    return ""


def _build_benchmark_context(state: dict) -> str:
    """Build benchmark info string from state."""
    benchmark_cmd = state.get("benchmark_cmd", "")
    if not benchmark_cmd:
        return ""
    scores = state.get("benchmark_scores", [])
    if scores:
        last = scores[-1]["score"]
        return f"""
**Benchmark**: `{benchmark_cmd}` (last score: {last})
The benchmark runs automatically after tests pass. Score is tracked across
iterations - lower is better. The trend is shown in the output."""
    return f"""
**Benchmark**: `{benchmark_cmd}` (no prior score - first run)
The benchmark runs automatically after tests pass. It must output a numeric
value. This score will be tracked across iterations - lower is better."""


def _build_spawn_instruction(agent_phase_key: str) -> tuple[str, str]:
    """Build spawn_instruction and spawn_instruction_plan from agent count.

    Returns (spawn_instruction, spawn_instruction_plan).
    """
    _NUM_WORDS = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE", 6: "SIX"}
    agent_count = len(_MODEL.agents.get(agent_phase_key, []))
    spawn_mode = "PARALLEL"  # all agents spawn in parallel
    if agent_count > 0:
        word = _NUM_WORDS.get(agent_count, str(agent_count))
        spawn_instruction = (
            f"**MANDATORY: Spawn {word} SEPARATE agents IN {spawn_mode}** "
            f"(single message, {word} Agent tool calls)."
        )
        spawn_instruction_plan = (
            f"**MANDATORY: Spawn {word} SEPARATE agents IN {spawn_mode} "
            f"to review the plan** (single message, {word} Agent tool calls)."
        )
    else:
        spawn_instruction = ""
        spawn_instruction_plan = ""
    return spawn_instruction, spawn_instruction_plan


def _build_context(state: dict | None = None, phase: str = "", event: str = "") -> dict:
    """Compute all template variables from state for phase rendering.

    This is the central factory that every phase callable uses to
    assemble the context dict for str.format_map(). Computes dynamic
    content from iteration state: prior failures, benchmark info,
    iteration plan. Also generates spawn instructions and agent
    instructions from phases.yaml.

    Args:
        state: current iteration state from state.yaml
        phase: phase name for agent instruction lookup
        event: 'start' or 'end' to select correct agent set
    """
    s = state or {}

    prior_context = _build_failures_context()
    plan_context = _build_plan_context(s)
    benchmark_info = _build_benchmark_context(s)

    # Iteration purpose - explains what this iteration is about
    iteration = s.get("iteration", 1)
    total_iters = s.get("total_iterations", 1)
    itype = s.get("type", _DEFAULT_CLI_NAME)
    iteration_plan = s.get("iteration_plan", "")
    wf_fqn = _CLI_TO_FQN.get(itype, itype)
    wf_def = _MODEL.workflow_types.get(wf_fqn)
    if wf_def and not wf_def.independent:
        iteration_purpose = "\n" + _msg("dependency_banner", description=wf_def.description) + "\n"
    elif iteration > 0 and iteration_plan:
        iteration_purpose = (
            "\n" + _msg("iteration_n_banner", iteration=iteration, total=total_iters) + "\n"
        )
    else:
        iteration_purpose = ""

    # Build hypothesis context for {prior_hyp}
    try:
        all_hyp = _load_hypotheses()
        if all_hyp:
            # Show deferred and new hypotheses (not dismissed/processed)
            active = {k: v for k, v in all_hyp.items() if v.get("status") in {"new", "deferred"}}
            if active:
                hyp_lines = ["\n**Prior hypotheses:**\n"]
                for hid, h in active.items():
                    text = h.get("hypothesis", "")
                    stars = h.get("stars", "")
                    status = h.get("status", "?")
                    hyp_lines.append(f"- **{hid}** [{status}]: {text} (stars: {stars})")
                prior_hyp = "\n".join(hyp_lines) + "\n"
            else:
                prior_hyp = ""
        else:
            prior_hyp = ""
    except Exception:
        prior_hyp = ""

    ctx = {
        "CMD": CMD,
        "objective": s.get("objective", "not set"),
        "iteration": iteration,
        "iteration_purpose": iteration_purpose,
        "total": total_iters,
        "remaining": total_iters - iteration,
        "prior_context": prior_context,
        "plan_context": plan_context,
        "checklist": _guardian_checklist(),
        "benchmark_info": benchmark_info,
        "prior_hyp": prior_hyp,
        "record_instructions": s.get("record_instructions", ""),
        "phase_dir": str(_phase_dir(s)),
        "artifacts_dir": str(DEFAULT_ARTIFACTS_DIR.resolve()),
    }
    # Agent instructions - resolve via :: namespace (FULL::PLAN has agents for end review)
    agent_phase_key = _resolve_agents(phase or s.get("current_phase", ""))
    ctx["agents_instructions"] = _build_agent_instructions(agent_phase_key, ctx)

    # Spawn instructions - derived from agent count
    spawn, spawn_plan = _build_spawn_instruction(agent_phase_key)
    ctx["spawn_instruction"] = spawn
    ctx["spawn_instruction_plan"] = spawn_plan

    return ctx


# ── Phase instruction registry (YAML-driven) ────────────────────────


def _make_phase_callable(phase: str, event: str) -> object:
    """Create a zero-arg callable that loads state and renders a phase template.

    Registered in _PHASE_START/_PHASE_END dicts, these closures are the
    bridge between YAML templates and the orchestrator. Each callable:
    1. Loads current state from disk
    2. Builds context via _build_context()
    3. Selects the right template (handles NEXT remaining conditionals)
    4. Renders the template with format_map()
    """

    def _callable():
        """Load state, build context, render the model Phase template for this phase/event."""
        state = _load_state()
        ctx = _build_context(state, phase=phase, event=event)
        resolved_phase = _resolve_phase(phase)
        # Handle conditional templates: phases with start_continue/start_final
        # variants use remaining-count logic to select the right template
        key = event
        _phase_obj = _MODEL.phases.get(resolved_phase)
        if _phase_obj and _phase_obj.start_continue:
            remaining = ctx["remaining"]
            if event == "start":
                key = "start_continue" if remaining > 0 else "start_final"
            elif event == "end":
                key = "end_continue" if remaining > 0 else "end_final"
        phase_obj = _MODEL.phases.get(resolved_phase)
        template = getattr(phase_obj, key, "") if phase_obj else ""
        if not template:
            template = f"Phase {phase} {event}"
        return template.format_map(collections.defaultdict(str, ctx))

    return _callable


# ── Auto-action handlers ──────────────────────────────────────────


def _action_iteration_summary(state: dict, phase: str):
    print("\n" + _msg("auto_separator"))
    print(_msg("auto_summary"))
    print(_msg("auto_separator"))
    _run_summary(state)
    nxt = _next_phase(state)
    if nxt:
        # Check if the next phase has conditional templates (iteration advance)
        resolved_nxt = _resolve_phase(nxt)
        nxt_obj = _MODEL.phases.get(resolved_nxt)
        if nxt_obj and nxt_obj.start_continue:
            print("\n" + _msg("auto_separator"))
            print(_msg("auto_next"))
            print(_msg("auto_autonomous"))
            print(_msg("auto_separator"))
            next_instructions = _PHASE_START.get(nxt, lambda: "")()
            print(next_instructions)


def _action_iteration_advance(state: dict, phase: str):
    _run_next_iteration(state)
    return "return"


def _action_plan_save(state: dict, phase: str):
    """Save PLAN output as plan.yaml for dependency workflows."""
    wf_fqn = _CLI_TO_FQN.get(state.get("type", ""), "")
    wf_def = _MODEL.workflow_types.get(wf_fqn)
    if not wf_def or wf_def.independent:
        return
    output_content = state.get("phase_outputs", {}).get(phase, "")
    if not output_content:
        return
    plan_file = DEFAULT_ARTIFACTS_DIR / "plan.yaml"
    plan_data = {
        "objective": state.get("objective", ""),
        "total_iterations": state.get("total_iterations", 1),
        "plan": output_content,
        "created_at": _now(),
    }
    plan_file.write_text(_yaml_dump(plan_data))
    print(_msg("plan_saved", path=plan_file))


def _run_auto_actions(phase: str, state: dict) -> bool:
    """Run auto_actions.on_complete for the resolved phase. Returns True if handler signalled early return.

    Actions are resolved in this order:
    1. Python handler in _AUTO_ACTION_REGISTRY (programmatic actions)
    2. Generative action definition in _MODEL.actions (runs via claude -p)
    """
    resolved = _resolve_phase(phase)
    phase_obj = _MODEL.phases.get(resolved)
    if not phase_obj or not phase_obj.auto_actions:
        return False
    actions = phase_obj.auto_actions.get("on_complete", [])
    for action_name in actions:
        # Try programmatic handler first
        handler = _AUTO_ACTION_REGISTRY.get(action_name)
        if handler:
            result = handler(state, phase)
            if result == "return":
                return True
            continue
        # Try generative action from model (lookup by cli_name)
        action_def = None
        for adef in _MODEL.actions.values():
            if adef.cli_name == action_name:
                action_def = adef
                break
        if action_def is None:
            action_def = _MODEL.actions.get(action_name)
        if action_def and action_def.type == "generative" and action_def.prompt:
            # Resolve template variables in prompt before execution
            template_vars = {
                "phase_output": state.get("phase_outputs", {}).get(phase, ""),
                "artifacts_dir": str(DEFAULT_ARTIFACTS_DIR),
                "iteration": str(state.get("iteration", "")),
            }
            resolved_prompt = action_def.prompt.format_map(
                collections.defaultdict(str, template_vars)
            )
            # Run generative action via claude -p subprocess
            _claude_evaluate(resolved_prompt, timeout=120)
    return False


# ── Helper functions ─────────────────────────────────────────────────


def _now() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_REQUIRED_STATE_KEYS = {
    "iteration",
    "total_iterations",
    "type",
    "objective",
    "benchmark_cmd",
    "current_phase",
    "phase_status",
    "record_instructions",
}

# ── Token counting ───────────────────────────────────────────────────

_TOKENIZER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_TOKENIZER.encode(text))


def _load_state() -> dict | None:
    """Load iteration state from state.yaml.

    Validates required keys are present. Old state files missing
    required keys will crash with a clear error.
    """
    if STATE_FILE.exists():
        state = yaml.safe_load(STATE_FILE.read_text())
        if state:
            missing = _REQUIRED_STATE_KEYS - set(state.keys())
            if missing:
                print(
                    f"ERROR: state.yaml is missing required keys: {', '.join(sorted(missing))}. "
                    "This state file is from an older version. "
                    "Run `orchestrate new` to start a fresh session.",
                    file=sys.stderr,
                )
                sys.exit(1)
        return state
    return None


def _yaml_dump(data: object) -> str:
    """Dump data to YAML with literal block style for readable output.

    Uses a custom LiteralStr type and YAML representer to output
    multiline strings as literal block scalars (|) instead of quoted
    strings. Long single-line strings are word-wrapped at 80 chars.
    This produces human-readable state.yaml and log.yaml files.
    """

    class LiteralStr(str):
        pass

    def _literal_representer(dumper, data):
        """YAML representer that outputs strings as literal block scalars."""
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")

    def _wrap_long(text: str, width: int = 80) -> str:
        """Wrap long single-line strings into multiline at sentence/clause boundaries."""
        if len(text) <= width:
            return text
        lines = []
        current = ""
        for word in text.split():
            if len(current) + len(word) + 1 > width:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            lines.append(current)
        return "\n".join(lines)

    def _prepare(obj):
        """Recursively convert long or multiline strings to LiteralStr."""
        if isinstance(obj, dict):
            return {k: _prepare(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_prepare(v) for v in obj]
        if isinstance(obj, str) and ("\n" in obj or len(obj) > 80):
            text = _wrap_long(obj) if "\n" not in obj else obj
            if not text.endswith("\n"):
                text += "\n"
            return LiteralStr(text)
        return obj

    dumper = yaml.Dumper
    dumper.add_representer(LiteralStr, _literal_representer)
    return yaml.dump(
        _prepare(data),
        Dumper=dumper,
        default_flow_style=False,
        sort_keys=False,
    )


def _save_state(state: dict) -> None:
    """Write current iteration state dict to state.yaml.

    Called after every state mutation (phase transitions, agent recording,
    gatekeeper results, rejections) to persist progress to disk.
    """
    STATE_FILE.write_text(_yaml_dump(state))


def _save_objective(objective: str, iterations: int) -> None:
    """Save objective to objective.yaml in artifacts dir."""
    obj_file = DEFAULT_ARTIFACTS_DIR / "objective.yaml"
    obj_file.write_text(
        _yaml_dump(
            {
                "objective": objective,
                "iterations": iterations,
                "created_at": _now(),
            }
        )
    )


def _load_yaml_list(path: Path) -> list[dict]:
    """Load a YAML file containing a list of entries."""
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text())
    return data if isinstance(data, list) else []


def _append_yaml_entry(path: Path, entry: dict) -> None:
    """Append an entry to a YAML list file."""
    entries = _load_yaml_list(path)
    entries.append(entry)
    path.write_text(_yaml_dump(entries))


def _append_log(entry: dict) -> None:
    """Append a timestamped entry to the audit log."""
    entry["timestamp"] = _now()
    _append_yaml_entry(LOG_FILE, entry)


def _append_failure(entry: dict) -> None:
    """Append a failure entry with auto-generated identifier."""
    failures = _load_failures()
    desc = entry.get("description", entry.get("mode", "failure"))
    fid = _generate_entry_id(desc, set(failures.keys()))
    failures[fid] = {
        "description": entry.get("description", ""),
        "context": entry.get("context", ""),
        "iteration": entry.get("iteration", 0),
        "phase": entry.get("phase", "unknown"),
        "mode": entry.get("mode", "?"),
        "status": "new",
        "notes": [],
        "solution": None,
        "timestamp": _now(),
    }
    _save_failures(failures)


def _load_context() -> dict:
    """Load context messages from context.yaml.

    Returns a dict mapping identifiers to rich entry dicts. Each entry
    contains: message, phase, created, acknowledged_by, processed.
    Raises ValueError if the file contains the old flat format.
    """
    if not CONTEXT_FILE.exists():
        return {}
    data = yaml.safe_load(CONTEXT_FILE.read_text())
    if not isinstance(data, dict):
        return {}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"context.yaml contains legacy flat format (key '{key}' maps to "
                f"{type(entry).__name__}, expected dict). "
                "Delete context.yaml and re-add entries with: "
                "orchestrate context --message '...' --phase PHASE"
            )
        required = {"message", "phase", "status"}
        missing = required - entry.keys()
        if missing:
            raise ValueError(
                f"context.yaml entry '{key}' missing required keys: {missing}. "
                "Delete context.yaml and re-add entries."
            )
        _VALID_STATUSES = {"new", "acknowledged", "dismissed", "processed"}
        if entry["status"] not in _VALID_STATUSES:
            raise ValueError(
                f"context.yaml entry '{key}' has invalid status '{entry['status']}'. "
                f"Must be one of: {sorted(_VALID_STATUSES)}"
            )
    return data


def _save_context(ctx: dict) -> None:
    """Save context messages to context.yaml."""
    CONTEXT_FILE.write_text(_yaml_dump(ctx))


_VALID_CONTEXT_TRANSITIONS = {
    "new": {"acknowledged", "dismissed", "processed"},
    "acknowledged": {"dismissed", "processed"},
    "dismissed": set(),  # terminal
    "processed": set(),  # terminal
}


def _load_failures() -> dict:
    """Load failures from failures.yaml as identifier-keyed dicts.
    Raises ValueError if file contains legacy flat list format.
    """
    if not FAILURES_FILE.exists():
        return {}
    data = yaml.safe_load(FAILURES_FILE.read_text())
    if not isinstance(data, dict):
        if isinstance(data, list):
            raise ValueError(
                "failures.yaml contains legacy flat list format. "
                "Delete failures.yaml and re-log failures."
            )
        return {}
    _VALID_FAILURE_STATUSES = {"new", "acknowledged", "dismissed", "processed"}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(f"failures.yaml entry '{key}' is not a dict.")
        status = entry.get("status", "")
        if status and status not in _VALID_FAILURE_STATUSES:
            raise ValueError(
                f"failures.yaml entry '{key}' has invalid status '{status}'. "
                f"Must be one of: {sorted(_VALID_FAILURE_STATUSES)}"
            )
    return data


def _save_failures(failures: dict) -> None:
    """Save failures to failures.yaml."""
    FAILURES_FILE.write_text(_yaml_dump(failures))


def _load_hypotheses() -> dict:
    """Load hypotheses from hypotheses.yaml as identifier-keyed dicts.
    Raises ValueError if file contains legacy flat list format.
    """
    hyp_file = DEFAULT_ARTIFACTS_DIR / "hypotheses.yaml" if DEFAULT_ARTIFACTS_DIR else None
    if not hyp_file or not hyp_file.exists():
        return {}
    data = yaml.safe_load(hyp_file.read_text())
    if not isinstance(data, dict):
        if isinstance(data, list):
            raise ValueError(
                "hypotheses.yaml contains legacy flat list format. "
                "Delete hypotheses.yaml and let the HYPOTHESIS phase regenerate."
            )
        return {}
    _VALID_HYP_STATUSES = {"new", "dismissed", "processed", "deferred"}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(f"hypotheses.yaml entry '{key}' is not a dict.")
        status = entry.get("status", "")
        if status and status not in _VALID_HYP_STATUSES:
            raise ValueError(
                f"hypotheses.yaml entry '{key}' has invalid status '{status}'. "
                f"Must be one of: {sorted(_VALID_HYP_STATUSES)}"
            )
        # Validate notes format: must be list of single-key dicts with valid status keys
        notes = entry.get("notes")
        if notes is not None:
            if not isinstance(notes, list):
                raise ValueError(
                    f"hypotheses.yaml entry '{key}' has non-list notes "
                    f"(got {type(notes).__name__}). Notes must be a list."
                )
            _VALID_NOTE_STATUSES = {"new", "dismissed", "processed", "deferred", "acknowledged"}
            for i, note in enumerate(notes):
                if isinstance(note, str):
                    raise ValueError(
                        f"hypotheses.yaml entry '{key}' has plain string notes. "
                        "Notes must be dicts: [{{status: 'message'}}]"
                    )
                if not isinstance(note, dict):
                    raise ValueError(
                        f"hypotheses.yaml entry '{key}' notes[{i}] is not a dict "
                        f"(got {type(note).__name__})."
                    )
                if len(note) != 1:
                    raise ValueError(
                        f"hypotheses.yaml entry '{key}' notes[{i}] must have exactly "
                        f"one key (got {len(note)})."
                    )
                note_key = next(iter(note))
                if note_key not in _VALID_NOTE_STATUSES:
                    raise ValueError(
                        f"hypotheses.yaml entry '{key}' notes[{i}] has invalid key "
                        f"'{note_key}'. Must be one of: {sorted(_VALID_NOTE_STATUSES)}"
                    )
    return data


def _save_hypotheses(hypotheses: dict) -> None:
    """Save hypotheses to hypotheses.yaml."""
    hyp_file = DEFAULT_ARTIFACTS_DIR / "hypotheses.yaml"
    hyp_file.write_text(_yaml_dump(hypotheses))


def _generate_entry_id(message: str, existing_ids: set, identifier: str = "") -> str:
    """Generate a short identifier from a message string.

    If *identifier* is provided, uses it directly (truncated to 37 chars)
    instead of slugifying the message. Falls back to 'ctx' for empty values.
    Appends _2, _3, ... on collision with existing_ids.
    """
    if identifier:
        # Use provided identifier, ensure uniqueness
        candidate = identifier.strip()[:37]
        if not candidate:
            candidate = "ctx"
    else:
        # Fall back to slugification
        slug = re.sub(r"[^a-z0-9]+", "_", message.lower()).strip("_")[:37]
        candidate = slug if slug else "ctx"
    base = candidate
    counter = 2
    while candidate in existing_ids:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _phase_dir(state: dict) -> Path:
    """Get/create phase artifacts subfolder: phase_N_NAME/."""
    itype = ITERATION_TYPES[state["type"]]
    phases = itype["phases"]
    phase = state["current_phase"]
    idx = phases.index(phase) + 1 if phase in phases else 0
    folder = DEFAULT_ARTIFACTS_DIR / f"phase_{idx:02d}_{phase.lower()}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()


def _next_phase(state: dict) -> str | None:
    """Return the next phase name in the workflow sequence.

    Looks up the current phase in ITERATION_TYPES and returns the
    following phase, or None if the current phase is the last one.
    Used by cmd_end to advance the state machine.
    """
    itype = ITERATION_TYPES[state["type"]]
    phases = itype["phases"]
    try:
        idx = phases.index(state["current_phase"])
        if idx + 1 < len(phases):
            return phases[idx + 1]
    except ValueError:
        pass
    return None


def _prev_implementable(state: dict) -> str:
    """Find the phase to return to when a reviewer rejects.

    Checks the current phase's reject_to declaration first. If not defined,
    walks backward through the phase sequence looking for the first phase
    that is a reject_to target of any phase in the workflow (i.e., a phase
    that other phases point back to on rejection). Falls back to the first
    phase in the workflow.
    """
    current = state["current_phase"]
    # Check current phase's reject_to first
    resolved = _resolve_phase(current)
    phase_obj = _MODEL.phases.get(resolved)
    if phase_obj and phase_obj.reject_to:
        target = phase_obj.reject_to.get("phase", "")
        if target:
            return target

    # Walk backward looking for a phase that is a rejection target
    itype = ITERATION_TYPES[state["type"]]
    phases = itype["phases"]
    wf_prefix = _workflow_prefix(state["type"])
    # Build set of phases that are reject_to targets in this workflow
    reject_targets: set[str] = set()
    for p in phases:
        try:
            p_resolved = resolve_phase_key(wf_prefix, p, set(_MODEL.phases.keys()))
        except KeyError:
            continue
        p_obj = _MODEL.phases.get(p_resolved)
        if p_obj and p_obj.reject_to:
            reject_targets.add(p_obj.reject_to.get("phase", ""))

    idx = phases.index(current)
    for i in range(idx - 1, -1, -1):
        if phases[i] in reject_targets:
            return phases[i]
    return phases[0]


def _count_iteration_failures(iteration: int) -> list[tuple[str, dict]]:
    """Return (fid, entry) pairs for a specific iteration."""
    return [(fid, e) for fid, e in _load_failures().items() if e.get("iteration") == iteration]


def _init_artifacts_dir(artifacts_dir: Path | None = None) -> None:
    """Initialise the artifacts directory and set global path variables.

    Mutates module-level STATE_FILE, LOG_FILE, FAILURES_FILE to point
    to the correct artifacts directory. Called once in main() before
    any command handler runs.
    """
    global STATE_FILE, LOG_FILE, FAILURES_FILE, CONTEXT_FILE  # noqa: PLW0603
    d = artifacts_dir or DEFAULT_ARTIFACTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    STATE_FILE = d / "state.yaml"
    LOG_FILE = d / "log.yaml"
    FAILURES_FILE = d / "failures.yaml"
    CONTEXT_FILE = d / "context.yaml"


def _read_last_iteration(artifacts_dir: Path | None = None) -> int:
    """Read the last iteration number before cleaning. Returns 0 if none."""
    d = artifacts_dir or DEFAULT_ARTIFACTS_DIR
    state_file = d / "state.yaml"
    if state_file.exists():
        try:
            return yaml.safe_load(state_file.read_text()).get("iteration", 0)
        except (yaml.YAMLError, KeyError, AttributeError):
            pass
    return 0


_CLEAN_PRESERVE = {
    "context.yaml",
    "failures.yaml",
    "hypotheses.yaml",
}  # files preserved across clean
_CLEAN_PRESERVE_DIRS = {"resources", "iterations"}  # directories preserved across clean


def _clean_artifacts_dir(artifacts_dir: Path | None = None, preserve_data: bool = True) -> None:
    """Clean artifacts directory for fresh run.

    When preserve_data=True (default, used by --continue): preserves context.yaml,
    failures.yaml, hypotheses.yaml, resources/, and iterations/.
    When preserve_data=False (fresh new): only preserves resources/ directory.
    Project-local resources contain user customizations that must always survive.
    """
    d = artifacts_dir or DEFAULT_ARTIFACTS_DIR
    preserve_files = _CLEAN_PRESERVE if preserve_data else set()
    preserve_dirs = _CLEAN_PRESERVE_DIRS if preserve_data else {"resources"}
    if d.exists():
        for f in d.iterdir():
            if f.is_file():
                if f.name in preserve_files:
                    continue
                f.unlink()
            elif f.is_dir():
                if f.name in preserve_dirs:
                    continue
                shutil.rmtree(f)
    d.mkdir(parents=True, exist_ok=True)


# ── Programmatic verification ────────────────────────────────────────


def _verify_test_phase(state: dict | None = None) -> tuple[bool, str]:
    """Run automated test suite, linter, and optional benchmark.

    Executed automatically during TEST phase's cmd_end. Runs make test
    and make lint with 120s timeout each. If a benchmark command is
    configured (via --benchmark on cmd_new), runs it after tests pass
    and tracks the numeric score across iterations.
    Failure auto-rejects back to IMPLEMENT phase.
    """
    results = []
    for cmd_name, cmd in [("test", "make test"), ("lint", "make lint")]:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(PROJECT_ROOT),
            )
            if result.returncode == 0:
                results.append(f"{cmd_name}: PASS")
            else:
                output = result.stdout[-500:] if result.stdout else result.stderr[-500:]
                results.append(f"{cmd_name}: FAIL\n{output}")
                return False, "\n".join(results)
        except subprocess.TimeoutExpired:
            results.append(f"{cmd_name}: TIMEOUT (120s)")
            return False, "\n".join(results)
        except FileNotFoundError:
            results.append(f"{cmd_name}: Makefile target not found, skipping")

    # Run benchmark if configured
    # The benchmark is always a generative instruction - text that tells the
    # orchestrating Claude what to evaluate. It is NOT a shell command.
    # Claude reads the referenced file, evaluates each checklist item,
    # updates the file, and reports the violation count.
    benchmark_cmd = (state or {}).get("benchmark_cmd", "")
    if benchmark_cmd:
        results.append(f"benchmark (generative): {benchmark_cmd}")
        results.append("  MANDATORY BENCHMARK EVALUATION:")
        results.append(
            "  1. Read the benchmark file and evaluate EVERY [ ] item against the codebase"
        )
        results.append("  2. Mark [x] for passing items, leave [ ] for failing items")
        results.append("  3. EDIT the benchmark file with updated marks")
        results.append("  4. UPDATE the Score Tracking table with this iteration's results")
        results.append("  5. Report: unchecked count, failed tests, composite score")
        results.append("  The orchestrating agent MUST edit the benchmark file before proceeding.")
        results.append("  FAILURE TO UPDATE THE FILE IS A BENCHMARK VIOLATION.")

    return True, "\n".join(results)


# ── Claude evaluation ────────────────────────────────────────────────

_RATE_LIMIT_PATTERNS = (
    "hit your limit",
    "rate limit",
    "too many requests",
    "Resource has been exhausted",
)

_RATE_LIMIT_BACKOFFS = (5, 15, 45)


def _claude_evaluate(
    prompt: str,
    timeout: int = 60,
) -> tuple[bool, str]:
    """Run claude -p with a PASS/FAIL evaluation prompt.

    Used by readback and gatekeeper gates for independent validation.
    Strips the CLAUDECODE environment variable to prevent subprocess
    hang (claude-agent-sdk detects it and enters degraded mode).
    Uses sonnet model with max-turns 3 and 60s timeout.
    Retries up to 3 times on rate-limit responses with exponential backoff.
    Logs every prompt+response to artifacts/logs/ for debugging.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    log_dir = DEFAULT_ARTIFACTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    max_attempts = len(_RATE_LIMIT_BACKOFFS) + 1
    for attempt in range(max_attempts):
        try:
            result = subprocess.run(
                [
                    "claude",
                    "-p",
                    prompt,
                    "--model",
                    "sonnet",
                    "--max-turns",
                    "3",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(PROJECT_ROOT),
            )
            output = result.stdout.strip()
            first_line = output.split("\n")[0].strip("*#> ").strip().upper()
            passed = first_line.startswith("PASS")
        except FileNotFoundError:
            passed, output = False, "FAIL: claude CLI not found."
            break
        except subprocess.TimeoutExpired:
            passed, output = False, f"FAIL: claude -p timed out ({timeout}s)."
            break

        # Check for rate-limit patterns in output
        output_lower = output.lower()
        is_rate_limited = any(pat.lower() in output_lower for pat in _RATE_LIMIT_PATTERNS)
        if is_rate_limited and attempt < len(_RATE_LIMIT_BACKOFFS):
            wait = _RATE_LIMIT_BACKOFFS[attempt]
            retry_msg = (
                f"Rate limit detected (attempt {attempt + 1}/{max_attempts}). "
                f"Retrying in {wait}s..."
            )
            print(retry_msg, file=sys.stderr)
            # Log the retry
            ts = _now().replace(":", "-")
            retry_log = log_dir / f"eval_retry_{ts}.log"
            retry_log.write_text(
                f"RATE LIMIT RETRY (attempt {attempt + 1})\nWait: {wait}s\n\nOUTPUT:\n{output}\n",
                encoding="utf-8",
            )
            time.sleep(wait)
            continue

        # Not rate-limited or retries exhausted
        break

    # Log for tracing
    ts = _now().replace(":", "-")
    log_file = log_dir / f"eval_{ts}.log"
    log_file.write_text(
        f"PROMPT:\n{prompt}\n\nRESPONSE:\n{output}\n\nRESULT: {'PASS' if passed else 'FAIL'}\n",
        encoding="utf-8",
    )

    return passed, output


def _readback_validate(
    phase: str,
    understanding: str,
    instructions: str,
) -> tuple[bool, str]:
    """Validate agent understanding before phase execution via claude -p.

    This is a BLOCKING gate at phase start. The agent provides a brief
    understanding of what the phase requires, and an independent Claude
    session evaluates whether it captures the essential requirements.
    If readback fails, the phase stays PENDING until retried.
    Prompt template loaded from phases.yaml gates.readback.
    """
    obj_line = ""
    action_part = instructions
    for marker in [
        "**Goal",
        "**MANDATORY",
        "**CRITICAL",
        "**Execution",
        "### Agent",
        "**Actions",
    ]:
        idx = instructions.find(marker)
        if idx >= 0:
            obj_line = instructions[:idx].replace("\n", " ").strip()[:150]
            action_part = instructions[idx:]
            break
    action_abbrev = action_part[:500].replace("\n", " ").strip()
    gate_key = _resolve_lifecycle_gate(phase, "start")
    gate_template = _MODEL.gates.get(gate_key)
    prompt = (gate_template.prompt if gate_template else "").format_map(
        collections.defaultdict(
            str,
            {
                "phase": phase,
                "objective": obj_line,
                "instructions": action_abbrev,
                "understanding": understanding,
            },
        )
    )
    return _claude_evaluate(prompt)


def _gatekeeper_validate(
    phase: str,
    state: dict,
    evidence: str = "",
) -> tuple[bool, str]:
    """Validate phase execution quality against exit criteria via claude -p.

    This is a BLOCKING gate at phase end. An independent Claude session
    evaluates whether the agent's evidence satisfies the phase's exit
    criteria. ASK response is treated as BLOCK (not pass) - the agent
    must retry with better evidence.
    Prompt template loaded from phases.yaml gates.gatekeeper.
    """
    agents = state.get("phase_agents", {}).get(phase, [])
    output = state.get("phase_outputs", {}).get(phase, "")
    readback = state.get("readbacks", {}).get(phase, {})
    agent_key = _resolve_agents(phase)
    required_agents = PHASE_AGENTS.get(agent_key, [])

    exit_fn = _PHASE_END.get(phase)
    exit_criteria = exit_fn() if exit_fn else f"No exit criteria defined for {phase}"

    gate_key = _resolve_lifecycle_gate(phase, "end")
    gate_template = _MODEL.gates.get(gate_key)
    prompt = (gate_template.prompt if gate_template else "").format_map(
        collections.defaultdict(
            str,
            {
                "phase": phase,
                "exit_criteria": exit_criteria[:400],
                "required_agents": ", ".join(required_agents) if required_agents else "none",
                "recorded_agents": ", ".join(agents) if agents else "NONE",
                "output_status": f"yes ({len(output)} chars)" if output else "no",
                "readback_status": "PASS"
                if readback.get("passed")
                else ("FAIL" if readback else "not done"),
                "benchmark_configured": "yes" if state.get("benchmark_cmd") else "no",
                "evidence": evidence if evidence else "(no report provided)",
            },
        )
    )
    passed, explanation = _claude_evaluate(prompt)

    # ASK response = BLOCK (not pass)
    first_line = explanation.split("\n")[0].strip("*#> ").strip().upper() if explanation else ""
    if first_line.startswith("ASK"):
        print("\n" + _msg("gatekeeper_question", explanation=explanation))
        return False, f"ASK: {explanation}"

    return passed, explanation


def _gatekeeper_evaluate_skip(
    phase: str,
    reason: str,
    state: dict,
) -> tuple[bool, str]:
    """Gatekeeper decides if a phase skip is justified."""
    objective = state.get("objective", "not set")
    iteration = state.get("iteration", "?")
    itype = state.get("type", "?")

    instructions_fn = _PHASE_START.get(phase)
    instructions = instructions_fn() if instructions_fn else f"Phase {phase}"
    abbrev = instructions[:300].replace("\n", " ").strip()

    skip_gate_name = next(iter(_MODEL.skip_gate_types), "gatekeeper_skip")
    gate_template = _MODEL.gates.get(skip_gate_name, None)
    prompt = (gate_template.prompt if gate_template else "").format_map(
        collections.defaultdict(
            str,
            {
                "phase": phase,
                "iteration": str(iteration),
                "itype": itype,
                "objective": objective[:150],
                "phase_purpose": abbrev,
                "reason": reason,
            },
        )
    )
    passed, output = _claude_evaluate(prompt)
    first_line = output.split("\n")[0].strip("*#> ").strip().upper() if output else ""
    approved = first_line.startswith("APPROVE")
    return approved, output


def _gatekeeper_evaluate_force_skip(
    phase: str,
    reason: str,
    state: dict,
) -> tuple[bool, str]:
    """Very conservative gatekeeper for force-skipping REQUIRED phases.

    Required phases exist for a reason. Force-skip should only be approved
    when:
    - The iteration is being stopped early (all work done)
    - The phase was already executed in substance
    - External constraint makes the phase impossible
    """
    iteration = state.get("iteration", "?")
    completed = state.get("completed_phases", [])

    # Use the second skip gate type (force variant) or fall back
    skip_gates = sorted(_MODEL.skip_gate_types)
    force_skip_name = (
        skip_gates[1]
        if len(skip_gates) > 1
        else skip_gates[0]
        if skip_gates
        else "gatekeeper_force_skip"
    )
    gate_template = _MODEL.gates.get(force_skip_name, None)
    prompt = (gate_template.prompt if gate_template else "").format_map(
        collections.defaultdict(
            str,
            {
                "phase": phase,
                "iteration": str(iteration),
                "completed_phases": ", ".join(completed) if completed else "none",
                "reason": reason,
            },
        )
    )
    passed, output = _claude_evaluate(prompt)
    first_line = output.split("\n")[0].strip("*#> ").strip().upper() if output else ""
    approved = first_line.startswith("APPROVE")
    return approved, output


# ── Banner and footer ───────────────────────────────────────────────


def _banner(phase: str, action: str, state: dict) -> str:
    """Render the phase header banner with iteration progress.

    Displays iteration number, phase position, objective, and a progress
    bar showing completed/current/pending phases. Template loaded from
    app.yaml banner.header. Called at the start of cmd_start and cmd_end.
    """
    iteration = state.get("iteration", "?")
    itype = state.get("type", "?")
    phases = ITERATION_TYPES[itype]["phases"]
    phase_idx = phases.index(phase) + 1 if phase in phases else 0
    total = len(phases)

    _banner_tmpl = _MODEL.app.banner
    progress_parts = []
    for p in phases:
        if p == phase:
            progress_parts.append(_banner_tmpl.progress_current.format_map({"p": p}))
        elif p in state.get("completed_phases", []):
            progress_parts.append(_banner_tmpl.progress_done.format_map({"p": p}))
        else:
            progress_parts.append(p)
    progress = " -> ".join(progress_parts)

    rejected = state.get("rejected_count", 0)
    reject_info = f" | REJECTED {rejected}x" if rejected else ""
    objective = state.get("objective", "")
    total_iters = state.get("total_iterations", 1)
    wf_fqn = _CLI_TO_FQN.get(itype, itype)
    wf_def = _MODEL.workflow_types.get(wf_fqn)
    if wf_def and not wf_def.independent:
        iter_label = itype.upper()
    elif total_iters == 0:
        iter_label = _msg("benchmark_driven_label", iteration=iteration)
    elif total_iters > 1:
        iter_label = f"{iteration}/{total_iters}"
    else:
        iter_label = str(iteration)

    template = _banner_tmpl.header
    ctx = {
        "header_line": _HDR_CHAR * _HDR_WIDTH,
        "iter_label": iter_label,
        "itype": itype,
        "action": action,
        "phase_idx": phase_idx,
        "total": total,
        "phase": phase,
        "reject_info": reject_info,
        "objective": objective,
        "progress": progress,
    }
    return template.format_map(collections.defaultdict(str, ctx))


def _footer(phase: str, status: str, state: dict) -> str:
    """Render the phase footer with next-step guidance.

    Three variants loaded from app.yaml: 'start' (reminds agent of
    claw commands), 'end' (directs to next phase), 'final' (last phase
    in iteration). Provides the command hints that guide autonomous
    execution through the phase sequence.
    """
    iteration = state.get("iteration", "?")
    itype = state.get("type", "?")
    _footer_tmpl = _MODEL.app.footer
    ctx = {
        "separator_line": _SEP_CHAR * _SEP_WIDTH,
        "iteration": iteration,
        "itype": itype,
        "phase": phase,
        "cmd": CMD,
    }

    if status == "start":
        return _footer_tmpl.start.format_map(collections.defaultdict(str, ctx))
    else:
        nxt = _next_phase(state)
        if nxt:
            ctx["nxt"] = nxt
            return _footer_tmpl.end.format_map(collections.defaultdict(str, ctx))
        else:
            return _footer_tmpl.final.format_map(collections.defaultdict(str, ctx))


# ── Auto-action helpers ──────────────────────────────────────────────


def _run_summary(state: dict) -> None:
    """Write iteration_N.md executive summary to artifacts directory.

    Auto-action triggered after RECORD phase completes. Compiles
    research findings, hypotheses, plan, implementation evidence,
    and review verdicts into a single markdown summary file for
    the iteration audit trail.
    """
    iteration = state["iteration"]
    outputs = state.get("phase_outputs", {})
    agents = state.get("phase_agents", {})
    readbacks = state.get("readbacks", {})
    rejected = state.get("rejected_count", 0)
    objective = state.get("objective", "not set")
    completed = state.get("completed_phases", [])
    itype = state.get("type", "?")

    iteration_plan = state.get("iteration_plan", "")
    scope = ""
    if iteration_plan:
        for line in iteration_plan.split("\n"):
            if f"ITERATION {iteration}:" in line.upper():
                scope = line.strip()
                break

    total_iters = state.get("total_iterations", 1)
    lines = [
        f"# Iteration {iteration}/{total_iters} - Executive Summary",
        "",
        f"**Scope**: {scope if scope else 'see plan'}<br>",
        f"**Objective**: {objective}<br>",
        f"**Type**: {itype}<br>",
        f"**Phases completed**: {', '.join(completed) if completed else 'none'}<br>",
        f"**Rejections**: {rejected}<br>",
        f"**Started**: {state.get('started_at', '?')}",
        "",
    ]

    for phase_name in completed:
        if phase_name in outputs:
            lines.append(f"## {phase_name.title()}")
            lines.append("")
            for line in outputs[phase_name].split("\n"):
                if line.strip() and not line.startswith(("#", "-", "|")):
                    lines.append(f"{line}<br>")
                else:
                    lines.append(line)
            lines.append("")

    lines.append("## Execution Metrics")
    lines.append("")
    if agents:
        total_agents = sum(len(v) for v in agents.values())
        lines.append(f"- {total_agents} agents spawned across {len(agents)} phases<br>")
        for p, agent_list in agents.items():
            lines.append(f"  - **{p}**: {', '.join(agent_list)}<br>")
    if readbacks:
        passed = sum(1 for r in readbacks.values() if r.get("passed"))
        lines.append(f"- Readbacks: {passed}/{len(readbacks)} passed<br>")
    gatekeepers = state.get("gatekeepers", {})
    if gatekeepers:
        gk_passed = sum(1 for g in gatekeepers.values() if g.get("passed"))
        lines.append(f"- Gatekeepers: {gk_passed}/{len(gatekeepers)} passed<br>")
    if rejected:
        lines.append(f"- Rejections: {rejected}<br>")
    lines.append("")

    failures = _count_iteration_failures(iteration)
    if failures:
        lines.append("## Failures")
        lines.append("")
        for fid, f in failures:
            lines.append(f"- [{fid}] {f.get('mode', '?')}: {f.get('description', '?')}")
        lines.append("")

    summary_path = DEFAULT_ARTIFACTS_DIR / f"iteration_{iteration}.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(_msg("summary_written", path=summary_path))


def _run_next_iteration(state: dict) -> None:
    """Advance to the next iteration after NEXT phase completes.

    Resets phase_outputs and phase_agents for the new iteration,
    preserves failure log, increments the iteration counter, and
    displays the new iteration info. If all requested iterations
    are done, reports completion.
    """
    total = state.get("total_iterations", 1)
    current = state["iteration"]

    # Run-until-complete mode: total == 0 means iterate until benchmark score reaches 0
    if total == 0:
        scores = state.get("benchmark_scores", [])
        last_score = scores[-1]["score"] if scores else None
        if last_score is not None and last_score == 0:
            print("\n" + _msg("iteration_complete", total=current))
            print(_msg("benchmark_complete"))
            return
        safety_cap = 20
        if _MODEL and hasattr(_MODEL.app, "config"):
            safety_cap = _MODEL.app.config.get("safety_cap_iterations", 20)
        if current >= safety_cap:
            print("\n" + _msg("benchmark_safety_cap", count=current))
            return
    else:
        remaining = total - current
        if remaining <= 0:
            print("\n" + _msg("iteration_complete", total=total))
            print(_msg("iteration_new_cmd", cmd=CMD, itype=state["type"]))
            return

    new_iteration = current + 1

    # Switch from dependency workflow to parent workflow after planning iteration completes
    parent = state.get("parent_type", "")
    if parent and parent != state["type"]:
        wf_fqn = _CLI_TO_FQN.get(state["type"], state["type"])
        wf_def = _MODEL.workflow_types.get(wf_fqn)
        if wf_def and not wf_def.independent:
            state["type"] = parent
            state.pop("parent_type", None)

    itype_info = ITERATION_TYPES[state["type"]]
    first_phase = itype_info["phases"][0]

    # Preserve iteration_plan from iteration 0
    # Look for plan output: first check iteration_plan state key (set by plan_save action),
    # then fall back to finding phase output from any phase with plan_save auto_action
    iteration_plan = state.get("iteration_plan", "")
    if not iteration_plan:
        phase_outputs = state.get("phase_outputs", {})
        for p_name, p_output in phase_outputs.items():
            p_resolved = _resolve_phase(p_name)
            p_obj = _MODEL.phases.get(p_resolved)
            if (
                p_obj
                and p_obj.auto_actions
                and "plan_save" in p_obj.auto_actions.get("on_complete", [])
            ):
                iteration_plan = p_output
                break

    state["iteration"] = new_iteration
    state["current_phase"] = first_phase
    state["phase_status"] = "pending"
    state["completed_phases"] = []
    state["skipped_phases"] = []
    state["rejected_count"] = 0
    state["started_at"] = _now()
    # Reset phase_outputs AND phase_agents for new iteration
    state["phase_outputs"] = {}
    state["phase_agents"] = {}
    if iteration_plan:
        state["iteration_plan"] = iteration_plan
    _save_state(state)
    _append_log(
        {
            "iteration": new_iteration,
            "type": state["type"],
            "event": "next_iteration",
            "objective": state["objective"],
        }
    )

    label = f"{new_iteration}/{total}" if total > 1 else str(new_iteration)
    print("\n" + _msg("iteration_started_short", iter_label=label, itype=state["type"]))
    print(_msg("iteration_objective", objective=state["objective"]))
    print(_msg("iteration_remaining", remaining=total - new_iteration))
    if iteration_plan:
        print("\n" + _msg("iteration_plan_header"))
        print(_msg("iteration_plan_content", plan=iteration_plan[:200]))

    prior_failures = _count_iteration_failures(current)
    if prior_failures:
        print("\n" + _msg("prior_failures_header_short", count=len(prior_failures)))
        for fid, f in prior_failures[-3:]:
            print(
                _msg(
                    "prior_failure_item",
                    mode=f.get("mode", "?"),
                    description=f.get("description", "?"),
                )
            )

    print("\n" + _msg("iteration_begin_short", cmd=CMD))


# ── Command functions ───────────────────────────────────────────────


def cmd_new(args) -> None:
    """Start a new iteration request.

    Creates initial state with objective, iteration count, type, and
    optional benchmark command. Auto-starts iteration 0 (planning)
    when multiple iterations are requested with 'full' type.
    Fresh start cleans prior artifacts. --continue preserves context,
    failures, hypotheses, and benchmark scores from the existing session.
    --restart preserves data like --continue but keeps the same iteration
    number (resets phases to beginning of that iteration).
    """
    itype = args.type
    if itype not in ITERATION_TYPES:
        print(
            f"Unknown type: {itype}. Choose: {', '.join(ITERATION_TYPES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Block dependency workflows from direct invocation
    wf_fqn = _CLI_TO_FQN.get(itype, itype)
    wf_def = _MODEL.workflow_types.get(wf_fqn)
    if wf_def and not wf_def.independent:
        print(_msg("dependency_blocked", itype=itype), file=sys.stderr)
        sys.exit(1)

    total_iterations = getattr(args, "iterations", 1)

    # --dry-run: validate and print execution plan, no state files
    if getattr(args, "dry_run", False):
        _dry_run(itype, total_iterations)
        return

    continue_session = getattr(args, "continue_session", False)
    restart_session = getattr(args, "restart_session", False)

    if continue_session or restart_session:
        # Continue/Restart: preserve data, load existing state
        old_state = _load_state()
        if not old_state:
            action = "continue" if continue_session else "restart"
            print(
                f"No existing session to {action}. Use 'orchestrate new' without flags.",
                file=sys.stderr,
            )
            sys.exit(1)
        if restart_session:
            iteration = old_state["iteration"]  # Same iteration
            print(
                f"Restarting iteration {iteration} from beginning."
                " Preserving context/failures/hypotheses.\n"
            )
        else:
            iteration = old_state["iteration"] + 1
            print(
                f"Continuing from iteration {old_state['iteration']}."
                " Preserving context/failures/hypotheses.\n"
            )
        benchmark_scores = old_state.get("benchmark_scores", [])
        # Optionally update objective/benchmark/iterations from args
        if not args.objective or args.objective == old_state.get("objective", ""):
            args.objective = old_state.get("objective", args.objective)
        if not getattr(args, "benchmark", ""):
            args.benchmark = old_state.get("benchmark_cmd", "")
        if total_iterations == 1:  # Default value - use old
            total_iterations = old_state.get("total_iterations", total_iterations)
        if not getattr(args, "record_instructions", ""):
            args.record_instructions = old_state.get("record_instructions", "")
    else:
        # Fresh start: clean and reset (only preserve resources/)
        _clean_artifacts_dir(preserve_data=False)
        print(_msg("cleaned") + "\n")
        iteration = 1
        benchmark_scores = []
        old_state = None

    # Auto-run dependency workflow (iteration 0) when configured
    run_type = itype
    if wf_def and wf_def.depends_on and total_iterations > 1:
        dep_wf = _MODEL.workflow_types.get(wf_def.depends_on)
        if dep_wf:
            iteration = 0
            run_type = dep_wf.cli_name or wf_def.depends_on

    type_info = ITERATION_TYPES[run_type]
    first_phase = type_info["phases"][0]

    objective = args.objective

    benchmark_cmd = getattr(args, "benchmark", "") or ""
    state = {
        "iteration": iteration,
        "total_iterations": total_iterations,
        "type": run_type,
        "objective": objective,
        "benchmark_cmd": benchmark_cmd,
        "benchmark_scores": benchmark_scores,
        "current_phase": first_phase,
        "phase_status": "pending",
        "completed_phases": [],
        "skipped_phases": [],
        "rejected_count": 0,
        "started_at": _now(),
        "phase_outputs": {},
        "phase_agents": {},
        "parent_type": itype if run_type != itype else "",
        "record_instructions": getattr(args, "record_instructions", ""),
    }
    _save_state(state)
    _save_objective(objective, total_iterations)
    _append_log(
        {
            "iteration": iteration,
            "type": run_type,
            "event": "new_iteration",
            "objective": objective,
        }
    )

    run_fqn = _CLI_TO_FQN.get(run_type, run_type)
    run_wf = _MODEL.workflow_types.get(run_fqn)
    if run_wf and not run_wf.independent:
        iter_label = f"{run_type.upper()} (before {total_iterations} iterations)"
    elif total_iterations > 1:
        iter_label = f"{iteration} of {total_iterations}"
    else:
        iter_label = str(iteration)
    print(
        _msg(
            "iteration_started",
            iter_label=iter_label,
            itype=run_type,
            description=type_info["description"],
        )
    )
    print("\n" + _msg("iteration_objective", objective=objective))
    if total_iterations > 1:
        print(_msg("iteration_requested", total=total_iterations))
    if run_wf and not run_wf.independent:
        print("\n" + _msg("dependency_purpose", description=run_wf.description))
    print("\n" + _msg("iteration_phases", phases=" -> ".join(type_info["phases"])))
    print(_msg("iteration_required", required=", ".join(type_info["required"])))
    if type_info["skippable"]:
        print(_msg("iteration_skippable", skippable=", ".join(type_info["skippable"])))

    # Show prior failures if any
    if old_state:
        prior_failures = _count_iteration_failures(old_state["iteration"])
        if prior_failures:
            print("\n" + _msg("prior_failures_header", count=len(prior_failures)))
            for fid, f in prior_failures[-3:]:
                print(
                    _msg(
                        "prior_failure_item_full",
                        mode=f.get("mode", "?"),
                        description=f.get("description", "?"),
                    )
                )

    # Session summary
    obj_trunc = objective[:50] + "..." if len(objective) > 50 else objective
    phase_count = len(type_info["phases"])
    iter_display = (
        "unlimited (safety cap: {})".format(_MODEL.app.config.get("safety_cap_iterations", 20))
        if total_iterations == 0
        else str(total_iterations)
    )
    bm_display = (
        "no"
        if not benchmark_cmd
        else "yes - "
        + benchmark_cmd.strip()[:50]
        + ("..." if len(benchmark_cmd.strip()) > 50 else "")
    )
    session_display = (
        f"continuing from iteration {old_state['iteration']}"
        if old_state and (continue_session or restart_session)
        else "fresh start"
    )
    print(
        _msg(
            "session_summary",
            summary_objective=obj_trunc,
            summary_workflow=f"{run_type} ({phase_count} phases)",
            summary_iterations=iter_display,
            summary_benchmark=bm_display,
            summary_session=session_display,
        )
    )

    print("\n" + _msg("iteration_begin", cmd=CMD))


def cmd_start(args) -> None:
    """Enter current phase with BLOCKING readback validation.

    Loads phase instructions from YAML, runs readback gate via claude -p
    to validate agent understanding, then displays the phase instructions
    with banner, agent definitions, and user context if provided.
    Phase stays PENDING if readback fails.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active_start"), file=sys.stderr)
        print(_msg("no_active_start_cmd", cmd=CMD), file=sys.stderr)
        sys.exit(1)

    phase = state["current_phase"]

    # FSM guards against starting from in_progress (raises ValueError)
    try:
        _fire_fsm(START, state)  # pending -> readback
    except ValueError:
        print(_msg("phase_in_progress", phase=phase), file=sys.stderr)
        print(_msg("phase_in_progress_cmd", cmd=CMD), file=sys.stderr)
        sys.exit(1)

    understanding = getattr(args, "understanding", None)
    if not understanding:
        print(_msg("understanding_required"), file=sys.stderr)
        print(_msg("understanding_required_cmd", cmd=CMD), file=sys.stderr)
        sys.exit(1)

    # Get phase instructions for readback validation
    instructions_fn = _PHASE_START.get(phase)
    instructions = instructions_fn() if instructions_fn else f"Phase {phase}"

    # BLOCKING readback validation
    print(_msg("readback_separator"))
    print(_msg("readback_validating", phase=phase))
    print(_msg("readback_separator"))
    passed, explanation = _readback_validate(
        phase,
        understanding,
        instructions,
    )

    # Save readback artifact (pass or fail)
    pdir = _phase_dir(state)
    readback_file = pdir / "readback.md"
    readback_file.write_text(
        f"# Readback - {phase}\n\n"
        f"## Agent Understanding\n{understanding}\n\n"
        f"## Validation Result\n{'PASS' if passed else 'FAIL'}\n\n"
        f"## Explanation\n{explanation}\n",
        encoding="utf-8",
    )

    # Update state with readback result
    if "readbacks" not in state:
        state["readbacks"] = {}
    state["readbacks"][phase] = {"passed": passed, "at": _now()}

    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "readback",
            "passed": passed,
        }
    )

    if not passed:
        # Readback failed - return to pending
        _fire_fsm(READBACK_FAIL, state)  # readback -> pending
        _save_state(state)
        print("\n" + _msg("readback_fail", phase=phase))
        print(_msg("readback_fail_reason", reason=explanation[:200]))
        print("\n" + _msg("readback_retry", cmd=CMD))
        return

    print(_msg("readback_pass", phase=phase) + "\n")

    # Readback passed - advance to in_progress via FSM
    _fire_fsm(READBACK_PASS, state)  # readback -> in_progress
    state["phase_started_at"] = _now()
    _save_state(state)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "phase_start",
        }
    )

    header = _banner(phase, "ENTERING", state)

    # Inject ALL user context from context.yaml (broadcast to all phases)
    body = instructions
    all_ctx = _load_context()
    if all_ctx:
        active_ctx = {
            cid: e for cid, e in all_ctx.items() if e.get("status") in {"new", "acknowledged"}
        }
        if active_ctx:
            count = len(active_ctx)
            body += f"\n\n{count} context message(s) active:\n"
            body += _msg("user_guidance_header_line") + "\n"
            body += _msg("user_guidance_header") + "\n"
            body += _msg("user_guidance_header_line") + "\n\n"
            for cid, entry in active_ctx.items():
                body += f"**[{cid}]**: {entry['message']}\n\n"
            body += _msg("user_guidance_instruction")

        # Transition new -> acknowledged (notes left empty for agents to fill via phase prompts)
        dirty = False
        for cid, entry in all_ctx.items():
            if entry.get("status") == "new":
                entry["status"] = "acknowledged"
                dirty = True
        if dirty:
            _save_context(all_ctx)

    # Transition new -> acknowledged on failures (notes left empty for agents to fill)
    all_failures = _load_failures()
    if all_failures:
        dirty_f = False
        for fid, entry in all_failures.items():
            if entry.get("status") == "new":
                entry["status"] = "acknowledged"
                dirty_f = True
        if dirty_f:
            _save_failures(all_failures)

    foot = _footer(phase, "start", state)
    print(header + body + foot)


def _validate_end_inputs(args, phase: str, state: dict) -> tuple:
    """Parse and validate cmd_end inputs: evidence, agents, output file.

    Returns (evidence, agents, output_file_path, output_content).
    Exits with error if validation fails.
    """
    evidence = getattr(args, "evidence", "") or ""
    agents_str = getattr(args, "agents", "") or ""
    output_file_str = getattr(args, "output_file", "") or ""

    # Resolve and validate --output-file
    output_file_path = None
    output_content = ""
    if output_file_str:
        p = Path(output_file_str)
        if p.is_absolute():
            output_file_path = p
        else:
            output_file_path = (_phase_dir(state) / p).resolve()
        if not output_file_path.exists():
            print(_msg("output_file_missing", path=output_file_path), file=sys.stderr)
            sys.exit(1)
        output_content = output_file_path.read_text(encoding="utf-8")

    # Parse agents
    agents = [a.strip() for a in agents_str.split(",") if a.strip()] if agents_str else []

    # Check required agents - resolve via :: namespace
    required_key = _resolve_agents(phase)
    required_agents = PHASE_AGENTS.get(required_key, [])
    if required_agents and agents:
        missing = [r for r in required_agents if r not in agents]
        if missing:
            print(_msg("missing_agents", phase=phase, missing=", ".join(missing)), file=sys.stderr)
            print(
                _msg("missing_agents_required", required=", ".join(required_agents)),
                file=sys.stderr,
            )
            sys.exit(1)
    elif required_agents and not agents:
        print(
            _msg("requires_agents", phase=phase, required=", ".join(required_agents)),
            file=sys.stderr,
        )
        print(_msg("requires_agents_provide", required=",".join(required_agents)), file=sys.stderr)
        sys.exit(1)

    return evidence, agents, output_file_path, output_content


def _record_phase_outputs(
    state: dict, phase: str, agents: list, output_file_path, output_content: str, evidence: str
) -> None:
    """Record agents and output file content into state, then save."""
    if agents:
        if "phase_agents" not in state:
            state["phase_agents"] = {}
        state["phase_agents"][phase] = agents

    if output_file_path:
        if "phase_outputs" not in state:
            state["phase_outputs"] = {}
        state["phase_outputs"][phase] = output_content

        # Save to phase subfolder as output.md ONLY if the output-file
        # is NOT already inside the phase directory (avoids duplicates)
        pdir = _phase_dir(state)
        if not str(output_file_path).startswith(str(pdir)):
            output_dest = pdir / "output.md"
            output_dest.write_text(
                f"# {phase} Output\n\n{output_content}\n",
                encoding="utf-8",
            )
    elif evidence:
        # Evidence stored as gap-fill only if no --output-file
        if "phase_outputs" not in state:
            state["phase_outputs"] = {}
        if phase not in state["phase_outputs"]:
            state["phase_outputs"][phase] = evidence

    _save_state(state)


def _handle_test_failure(state: dict, phase: str, output: str) -> None:
    """Handle TEST phase auto-reject: FSM transitions, log failure, print messages."""
    target = _prev_implementable(state)
    _fire_fsm(END, state)  # in_progress -> gatekeeper
    _fire_fsm(GATE_FAIL, state)  # gatekeeper -> in_progress
    _fire_fsm(REJECT, state)  # in_progress -> rejected
    _fire_fsm(ADVANCE, state)  # rejected -> pending
    state["current_phase"] = target
    state["rejected_count"] = state.get("rejected_count", 0) + 1
    state.pop("phase_started_at", None)
    _save_state(state)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "auto_reject",
            "reason": "tests/lint failed",
            "target": target,
        }
    )
    _append_failure(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "mode": "FM-TEST-FAIL",
            "description": output[:200],
        }
    )
    print("\n" + _msg("tests_fail", target=target))
    print(_msg("tests_fail_run", cmd=CMD))


def _run_end_gatekeeper(phase: str, state: dict, evidence: str) -> tuple[bool, str]:
    """Fire FSM END event, run gatekeeper validation, save artifact, handle pass/fail.

    Returns (gk_passed, gk_output). On failure, prints messages and saves state.
    """
    _fire_fsm(END, state)  # in_progress -> gatekeeper
    print("\n" + _msg("gatekeeper_separator"))
    print(_msg("gatekeeper_evaluating", phase=phase))
    print(_msg("gatekeeper_separator"))
    gk_passed, gk_output = _gatekeeper_validate(
        phase,
        state,
        evidence,
    )

    # Save gatekeeper result to phase subfolder
    pdir = _phase_dir(state)
    gk_file = pdir / "gatekeeper.md"
    gk_file.write_text(
        f"# Gatekeeper - {phase}\n\n"
        f"## Result\n{'PASS' if gk_passed else 'FAIL'}\n\n"
        f"## Evaluation\n{gk_output}\n",
        encoding="utf-8",
    )

    # Update state
    if "gatekeepers" not in state:
        state["gatekeepers"] = {}
    state["gatekeepers"][phase] = {
        "passed": gk_passed,
        "at": _now(),
    }
    _save_state(state)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "gatekeeper",
            "passed": gk_passed,
        }
    )

    if not gk_passed:
        _fire_fsm(GATE_FAIL, state)  # gatekeeper -> in_progress (retry)
        _save_state(state)
        print("\n" + _msg("gatekeeper_fail", phase=phase))
        print(_msg("gatekeeper_fail_reason", reason=gk_output[:300]))
        print("\n" + _msg("gatekeeper_fail_retry", cmd=CMD))

    return gk_passed, gk_output


def _advance_phase(state: dict, phase: str) -> None:
    """Mark phase complete, advance FSM to next phase or iteration_complete."""
    _fire_fsm(GATE_PASS, state)  # gatekeeper -> complete
    print(_msg("gatekeeper_pass", phase=phase))

    state["completed_phases"].append(phase)
    started_at = state.get("phase_started_at", "")

    nxt = _next_phase(state)
    if nxt:
        _fire_fsm(ADVANCE, state)  # complete -> pending
        state["current_phase"] = nxt
    else:
        state["phase_status"] = "iteration_complete"

    state.pop("phase_started_at", None)
    _save_state(state)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "phase_complete",
            "started_at": started_at,
        }
    )


def _print_phase_summary(state: dict, phase: str) -> None:
    """Print executive summary of completed phase."""
    outputs = state.get("phase_outputs", {})
    agents_map = state.get("phase_agents", {})
    readbacks = state.get("readbacks", {})
    gatekeepers = state.get("gatekeepers", {})
    summary_lines = ["\n" + _msg("phase_complete", phase=phase)]
    if phase in outputs:
        out_text = outputs[phase]
        summary_lines.append(_msg("phase_output", output=out_text[:100]))
    if phase in agents_map:
        summary_lines.append(_msg("phase_agents", agents=", ".join(agents_map[phase])))
    if phase in readbacks:
        rb = readbacks[phase]
        summary_lines.append(_msg("phase_readback", status="PASS" if rb.get("passed") else "FAIL"))
    if phase in gatekeepers:
        gk = gatekeepers[phase]
        summary_lines.append(
            _msg("phase_gatekeeper", status="PASS" if gk.get("passed") else "FAIL")
        )
    print("\n".join(summary_lines))


def _check_note_richness(phase: str) -> None:
    """Check that acknowledged/dismissed/processed entries have rich notes (>= 50 tokens).

    Called at every phase end. Entries that transitioned from 'new' must have
    substantive notes explaining what was done - not just 'seen by PHASE'.
    """
    cfg = _MODEL.app.config if _MODEL else {}
    min_tokens = cfg.get("note_min_tokens", 50)

    errors = []
    # Check context entries
    try:
        ctx = _load_context()
        for cid, entry in ctx.items():
            if entry.get("status") in {"acknowledged", "dismissed", "processed"}:
                notes = entry.get("notes", [])
                if not notes:
                    errors.append(f"Context '{cid}': status '{entry['status']}' but no notes")
                    continue
                # Check the latest note has enough tokens
                latest = notes[-1]
                if isinstance(latest, dict):
                    note_text = str(list(latest.values())[0]) if latest else ""
                else:
                    note_text = str(latest)
                tokens = _count_tokens(note_text)
                if tokens < min_tokens:
                    errors.append(
                        f"Context '{cid}': latest note too short "
                        f"({tokens} tokens, minimum {min_tokens})"
                    )
    except (ValueError, FileNotFoundError):
        pass

    # Check failure entries
    try:
        failures = _load_failures()
        for fid, entry in failures.items():
            if entry.get("status") in {"acknowledged", "dismissed", "processed"}:
                notes = entry.get("notes", [])
                if not notes:
                    errors.append(f"Failure '{fid}': status '{entry['status']}' but no notes")
                    continue
                latest = notes[-1]
                if isinstance(latest, dict):
                    note_text = str(list(latest.values())[0]) if latest else ""
                else:
                    note_text = str(latest)
                tokens = _count_tokens(note_text)
                if tokens < min_tokens:
                    errors.append(
                        f"Failure '{fid}': latest note too short "
                        f"({tokens} tokens, minimum {min_tokens})"
                    )
    except (ValueError, FileNotFoundError):
        pass

    if errors:
        print("ERROR: note richness validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


def _check_lifecycle_compliance(phase: str, state: dict) -> None:
    """Check lifecycle compliance for phase-specific data.

    Called before gatekeeper. Hard programmatic gate - not LLM-dependent.
    """
    # ALL phases: check note richness on context and failure entries
    # Every acknowledged/dismissed/processed entry must have notes with >= 50 tokens
    _check_note_richness(phase)

    # NEXT phase: all context/failure items must be processed (no "new" or "acknowledged")
    if phase == "NEXT" or (
        state.get("completed_phases") and "RECORD" in state.get("completed_phases", [])
    ):
        try:
            ctx = _load_context()
            blocked_ctx = [
                cid for cid, e in ctx.items() if e.get("status") in {"new", "acknowledged"}
            ]
            if blocked_ctx:
                print(
                    f"ERROR: {len(blocked_ctx)} context item(s) still unprocessed: "
                    f"{', '.join(blocked_ctx)}",
                    file=sys.stderr,
                )
                print(
                    "All context/failure entries must be processed or dismissed "
                    "before iteration ends.",
                    file=sys.stderr,
                )
                sys.exit(1)
        except (ValueError, FileNotFoundError):
            pass  # No context file or invalid - not a compliance issue

        try:
            failures = _load_failures()
            blocked_failures = [
                fid for fid, e in failures.items() if e.get("status") in {"new", "acknowledged"}
            ]
            if blocked_failures:
                print(
                    f"ERROR: {len(blocked_failures)} failure(s) still unprocessed: "
                    f"{', '.join(blocked_failures)}",
                    file=sys.stderr,
                )
                print(
                    "All context/failure entries must be processed or dismissed "
                    "before iteration ends.",
                    file=sys.stderr,
                )
                sys.exit(1)
        except (ValueError, FileNotFoundError):
            pass  # No failures file or invalid - not a compliance issue

    # HYPOTHESIS phase: all hypotheses must be classified (no "new")
    if "HYPOTHESIS" in phase.upper():
        try:
            hyps = _load_hypotheses()
            new_hyps = [hid for hid, h in hyps.items() if h.get("status") == "new"]
            if new_hyps:
                print(
                    f"ERROR: {len(new_hyps)} hypothesis(es) still have status 'new': "
                    f"{', '.join(new_hyps)}",
                    file=sys.stderr,
                )
                print(
                    "All hypotheses must be processed, dismissed, or deferred before exiting.",
                    file=sys.stderr,
                )
                sys.exit(1)
            # Validate richness of non-dismissed hypotheses
            richness_errors = _validate_hypothesis_richness(hyps)
            if richness_errors:
                print("ERROR: hypothesis richness validation failed:", file=sys.stderr)
                for err in richness_errors:
                    print(f"  - {err}", file=sys.stderr)
                sys.exit(1)
            # Check notes on non-new items
            missing_notes = [
                hid for hid, h in hyps.items() if h.get("status") != "new" and not h.get("notes")
            ]
            if missing_notes:
                print(
                    f"WARNING: {len(missing_notes)} hypothesis(es) missing notes: "
                    f"{', '.join(missing_notes)}",
                    file=sys.stderr,
                )
            # Auto-dismiss expired deferred hypotheses
            max_deferred = 3
            if _MODEL and hasattr(_MODEL.app, "config"):
                max_deferred = _MODEL.app.config.get("hypothesis_max_deferred_iterations", 3)
            current_iter = state.get("iteration", 0)
            for hid, h in hyps.items():
                if h.get("status") == "deferred":
                    created = h.get("iteration_created", current_iter)
                    if current_iter - created > max_deferred:
                        h["status"] = "dismissed"
                        if not isinstance(h.get("notes"), list):
                            h["notes"] = []
                        h["notes"].append(
                            {"dismissed": f"exceeded max deferred iterations ({max_deferred})"}
                        )
            _save_hypotheses(hyps)

            # Richness validation: fields must have substance
            richness_errors = _validate_hypothesis_richness(hyps)
            if richness_errors:
                print("ERROR: Hypothesis richness validation failed:", file=sys.stderr)
                for err in richness_errors:
                    print(f"  - {err}", file=sys.stderr)
                sys.exit(1)
        except (ValueError, FileNotFoundError):
            pass


def _validate_research_output(output_content: str) -> list[str]:
    """Validate research output for required sections, token count, and file refs.

    Thresholds loaded from app.yaml config (quality floors).
    Returns list of error strings (empty = valid).
    """
    cfg = _MODEL.app.config if _MODEL else {}
    min_tokens = cfg.get("research_min_tokens", 500)
    section_min_tokens = cfg.get("research_section_min_tokens", 50)
    min_file_refs = cfg.get("research_min_file_refs", 5)

    errors = []
    required_sections = ["current state", "gap analysis", "file inventory", "risk assessment"]
    output_lower = output_content.lower()

    # Check section headers present
    for section in required_sections:
        if section not in output_lower:
            errors.append(f"Missing required section: {section}")

    # Check total token count
    total_tokens = _count_tokens(output_content)
    if total_tokens < min_tokens:
        errors.append(f"Research output too short ({total_tokens} tokens, minimum {min_tokens})")

    # Check file path references (word/word.ext pattern)
    file_refs = re.findall(r"[\w/]+\.\w+", output_content)
    if len(file_refs) < min_file_refs:
        errors.append(f"Too few file path references ({len(file_refs)}, minimum {min_file_refs})")

    # Check each section has >= 50 tokens content
    section_positions = []
    for section in required_sections:
        idx = output_lower.find(section)
        if idx >= 0:
            section_positions.append((idx, section))
    section_positions.sort(key=lambda x: x[0])

    for i, (pos, name) in enumerate(section_positions):
        header_end = output_content.find("\n", pos)
        if header_end < 0:
            header_end = pos + len(name)
        content_start = header_end + 1
        if i + 1 < len(section_positions):
            content_end = section_positions[i + 1][0]
        else:
            content_end = len(output_content)
        section_content = output_content[content_start:content_end].strip()
        section_tokens = _count_tokens(section_content)
        if section_tokens < section_min_tokens:
            errors.append(
                f"Section '{name}' too short ({section_tokens} tokens, minimum {section_min_tokens})"
            )

    return errors


_PREDICTION_COMPARISON_PATTERN = re.compile(
    r"(?:\d|from|to|increase|decrease|reduce)", re.IGNORECASE
)


def _validate_hypothesis_richness(hypotheses: dict) -> list[str]:
    """Validate hypothesis entries for field richness.

    Per entry (skipping dismissed and deferred):
    - hypothesis field >= hypothesis_min_tokens (from app.yaml, default 25)
    - prediction field >= prediction_min_tokens (from app.yaml, default 15) + contains number/comparison
    - evidence field >= evidence_min_tokens (from app.yaml, default 15)
    - stars is int 1-5

    Thresholds loaded from app.yaml config (quality floors only, no ceiling).
    Returns list of error strings (empty = valid).
    """
    cfg = _MODEL.app.config if _MODEL else {}
    hyp_min = cfg.get("hypothesis_min_tokens", 25)
    pred_min = cfg.get("prediction_min_tokens", 15)
    evidence_min = cfg.get("evidence_min_tokens", 15)

    errors = []
    for hid, entry in hypotheses.items():
        if entry.get("status") in {"dismissed", "deferred"}:
            continue
        hyp_text = entry.get("hypothesis", "")
        hyp_tokens = _count_tokens(hyp_text)
        if hyp_tokens < hyp_min:
            errors.append(
                f"Hypothesis '{hid}': hypothesis too short ({hyp_tokens} tokens, minimum {hyp_min}). "
                f"A hypothesis must be a real problem statement with root cause analysis."
            )
        pred_text = entry.get("prediction", "")
        pred_tokens = _count_tokens(pred_text)
        if pred_tokens < pred_min:
            errors.append(
                f"Hypothesis '{hid}': prediction too short ({pred_tokens} tokens, minimum {pred_min}). "
                f"Must be a specific measurable outcome."
            )
        elif not _PREDICTION_COMPARISON_PATTERN.search(pred_text):
            errors.append(
                f"Hypothesis '{hid}': prediction must contain a digit or comparison word "
                f"(from/to/increase/decrease/reduce)"
            )
        evidence_text = entry.get("evidence", "")
        evidence_tokens = _count_tokens(evidence_text)
        if evidence_tokens < evidence_min:
            errors.append(
                f"Hypothesis '{hid}': evidence too short ({evidence_tokens} tokens, minimum {evidence_min}). "
                f"Must reference concrete data points or code."
            )
        stars = entry.get("stars")
        if not isinstance(stars, int) or stars < 1 or stars > 5:
            errors.append(f"Hypothesis '{hid}': stars must be int 1-5 (got {stars!r})")
    return errors


def cmd_end(args) -> None:
    """Complete current phase with gatekeeper validation.

    Validates --agents against required agents from phases.yaml,
    records output file content, runs TEST automation if in TEST phase,
    runs gatekeeper gate for quality validation, then advances to
    next phase. Auto-actions: summary after RECORD, inline NEXT
    display after RECORD.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active"), file=sys.stderr)
        sys.exit(1)

    phase = state["current_phase"]
    if state["phase_status"] != "in_progress":
        print(_msg("phase_not_started", phase=phase), file=sys.stderr)
        print(_msg("phase_not_started_cmd", cmd=CMD), file=sys.stderr)
        sys.exit(1)

    evidence, agents, output_file_path, output_content = _validate_end_inputs(args, phase, state)
    _record_phase_outputs(state, phase, agents, output_file_path, output_content, evidence)

    header = _banner(phase, "COMPLETING", state)

    # ── Auto-verify phase: run programmatic verification (make test/lint) ──
    resolved_phase = _resolve_phase(phase)
    phase_obj = _MODEL.phases.get(resolved_phase)
    if phase_obj and phase_obj.auto_verify:
        print(header)
        body = _PHASE_END.get(phase, lambda: "")()
        print(body)

        passed, output = _verify_test_phase(state)
        print(output)

        if not passed:
            _handle_test_failure(state, phase, output)
            return

        print("\n" + _msg("tests_pass"))

    else:
        body = _PHASE_END.get(phase, lambda: "")()
        print(header + body)

    # ── Research output structural validation ──
    if "RESEARCH" in phase.upper() and output_content:
        research_errors = _validate_research_output(output_content)
        if research_errors:
            print("ERROR: Research output failed structural validation:", file=sys.stderr)
            for err in research_errors:
                print(f"  - {err}", file=sys.stderr)
            sys.exit(1)

    # ── Lifecycle compliance: hard programmatic gate ──
    _check_lifecycle_compliance(phase, state)

    # ── Gatekeeper: per-phase generative validation ──
    gk_passed, _gk_output = _run_end_gatekeeper(phase, state, evidence)
    if not gk_passed:
        return

    _advance_phase(state, phase)
    _print_phase_summary(state, phase)

    # ── Auto-actions from phases.yaml auto_actions.on_complete ──
    if _run_auto_actions(phase, state):
        return

    print(_footer(phase, "end", state))


def cmd_status(args) -> None:
    """Show current iteration state with phase progress.

    Displays iteration info, phase checklist with completion markers,
    agents recorded per phase, failures logged, and next command hint.
    Useful for resuming work after context loss.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active"))
        print("\n" + _msg("no_active_start_full", cmd=CMD))
        print("\n" + _msg("available_types"))
        for name, info in ITERATION_TYPES.items():
            print(_msg("available_type_item", name=name, description=info["description"]))
        return

    wf_type = state["type"]
    itype = ITERATION_TYPES[wf_type]
    phases = itype["phases"]
    total_iters = state.get("total_iterations", 1)
    iteration = state.get("iteration", "?")

    wf_fqn = _CLI_TO_FQN.get(wf_type, wf_type)
    wf_def = _MODEL.workflow_types.get(wf_fqn)
    if wf_def and not wf_def.independent:
        iter_label = wf_type.upper()
    elif total_iters == 0:
        iter_label = f"until benchmark complete (iteration {iteration})"
    elif total_iters > 1:
        iter_label = f"{iteration}/{total_iters}"
    else:
        iter_label = str(iteration)

    print(_msg("status_header", iter_label=iter_label, itype=wf_type))
    print(_msg("status_objective", objective=state.get("objective", "?")))
    print(_msg("status_started", started=state.get("started_at", "?")))
    print(_msg("status_current", phase=state["current_phase"], status=state["phase_status"]))
    rejected = state.get("rejected_count", 0)
    if rejected:
        print(_msg("status_rejections", count=rejected))
        lr = state.get("last_rejection", {})
        if lr:
            print(
                _msg(
                    "status_last_reject",
                    from_phase=lr.get("from", "?"),
                    reason=lr.get("reason", "?"),
                )
            )
    print()

    for p in phases:
        if p in state["completed_phases"]:
            marker = "[x]"
        elif p == state["current_phase"]:
            marker = "[>]" if state["phase_status"] == "in_progress" else "[ ]"
        elif any(s["phase"] == p for s in state.get("skipped_phases", [])):
            marker = "[-]"
        else:
            marker = "[ ]"
        req = "*" if p in itype["required"] else " "
        print(_msg("status_phase_item", marker=marker, p=p, req=req))

    # Show agents recorded per phase
    agents_map = state.get("phase_agents", {})
    if agents_map:
        print("\n" + _msg("status_agents_header"))
        for p, agent_list in agents_map.items():
            print(_msg("status_agent_item", phase=p, agents=", ".join(agent_list)))

    # Show failures for this iteration
    failures = _count_iteration_failures(state["iteration"])
    if failures:
        print("\n" + _msg("status_failures_header", count=len(failures)))
        for fid, f in failures:
            status = f.get("status", "new")
            status_tag = f" [{status.upper()}]" if status != "new" else ""
            print(f"  [{fid}] {f.get('mode', '?')}: {f.get('description', '?')[:60]}{status_tag}")

    # Show context messages with status and latest note
    all_ctx = _load_context()
    if all_ctx:
        print("\nContext messages:")
        for cid, entry in all_ctx.items():
            msg = entry.get("message", "")
            p = entry.get("phase", "?")
            created = entry.get("created", "?")[:10]
            status = entry.get("status", "?")
            notes = entry.get("notes", [])
            latest_note = ""
            if notes:
                last = notes[-1]
                latest_note = (
                    next(iter(last.values()), "") if isinstance(last, dict) else str(last)
                )
            truncated = msg[:60]
            ellipsis = "..." if len(msg) > 60 else ""
            print(
                f"  [{cid}] ({p}): {truncated}{ellipsis} (created: {created}, status: {status}) {latest_note[:40]}"
            )

    print("\n" + _msg("status_required_note"))
    if state["phase_status"] == "pending":
        print("\n" + _msg("status_next_start", cmd=CMD))
    elif state["phase_status"] == "in_progress":
        print("\n" + _msg("status_next_end", cmd=CMD))


def cmd_reject(args) -> None:
    """Critic rejects current phase, returning to an earlier phase.

    Rolls back to the most recent IMPLEMENT phase in the sequence,
    increments rejection count, and logs the rejection reason.
    Used when review agents find issues that need fixing.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active"), file=sys.stderr)
        sys.exit(1)

    phase = state["current_phase"]
    reason = args.reason or "no reason given"

    # Check reject_to declaration on current phase
    resolved = _resolve_phase(phase)
    phase_obj = _MODEL.phases.get(resolved)
    if phase_obj and phase_obj.reject_to:
        target = phase_obj.reject_to.get("phase", _prev_implementable(state))
    else:
        target = _prev_implementable(state)

    # FSM: reject current phase and advance to target
    _fire_fsm(REJECT, state)  # in_progress -> rejected
    _fire_fsm(ADVANCE, state)  # rejected -> pending
    state["current_phase"] = target
    state["rejected_count"] = state.get("rejected_count", 0) + 1
    state["last_rejection"] = {
        "from": phase,
        "reason": reason,
        "at": _now(),
    }
    state.pop("phase_started_at", None)
    _save_state(state)

    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "rejected",
            "reason": reason,
            "target": target,
        }
    )

    print("\n" + _msg("reject_header", phase=phase, target=target))
    print(_msg("reject_reason", reason=reason))
    print(_msg("reject_count", count=state["rejected_count"]))
    print("\n" + _msg("reject_fix", cmd=CMD))


def cmd_skip(args) -> None:
    """Skip an optional phase or force-skip a required one.

    Optional phases (skippable: true in workflow.yaml) can be
    skipped with gatekeeper approval. Required phases need --force
    flag and pass a conservative gatekeeper that defaults to DENY.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active"), file=sys.stderr)
        sys.exit(1)

    phase = state["current_phase"]
    itype = ITERATION_TYPES[state["type"]]
    force = getattr(args, "force", False)

    if phase in itype["required"] and not force:
        print(_msg("skip_blocked", phase=phase, itype=state["type"]), file=sys.stderr)
        print(
            _msg("skip_blocked_required", required=", ".join(itype["required"])), file=sys.stderr
        )
        print("\n" + _msg("skip_blocked_force"), file=sys.stderr)
        sys.exit(1)

    reason = args.reason or "no reason given"
    is_required = phase in itype["required"]

    print(_msg("gatekeeper_skip_separator"))
    label = "FORCE-SKIP (required phase)" if is_required else "SKIP"
    print(_msg("gatekeeper_skip_evaluating", label=label, phase=phase))
    print(_msg("gatekeeper_skip_separator"))

    if is_required:
        approved, explanation = _gatekeeper_evaluate_force_skip(
            phase,
            reason,
            state,
        )
    else:
        approved, explanation = _gatekeeper_evaluate_skip(
            phase,
            reason,
            state,
        )

    if not approved:
        print("\n" + _msg("gatekeeper_skip_denied", phase=phase))
        print(_msg("gatekeeper_skip_denied_reason", reason=explanation[:300]))
        print("\n" + _msg("gatekeeper_skip_denied_retry", cmd=CMD))
        _append_log(
            {
                "iteration": state["iteration"],
                "phase": phase,
                "event": "skip_denied",
                "reason": reason,
                "gatekeeper": explanation[:200],
            }
        )
        return

    print(_msg("gatekeeper_skip_approved", phase=phase))

    state["skipped_phases"].append({"phase": phase, "reason": reason})

    # FSM: skip and advance
    _fire_fsm(SKIP, state)  # pending -> skipped
    nxt = _next_phase(state)
    if nxt:
        _fire_fsm(ADVANCE, state)  # skipped -> pending
        state["current_phase"] = nxt
    else:
        state["phase_status"] = "iteration_complete"

    _save_state(state)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "phase_skipped",
            "reason": reason,
            "gatekeeper": "approved",
        }
    )

    print(_msg("skip_approved_msg", phase=phase, reason=reason))
    if nxt:
        print("\n" + _msg("skip_next", nxt=nxt))
        print(_msg("skip_next_cmd", cmd=CMD))
    else:
        print("\n" + _msg("skip_iteration_complete"))


def cmd_context(args) -> None:
    """Inject user guidance into a phase, broadcast to all agents.

    Stores the user's message in context.yaml as a rich entry keyed
    by auto-generated identifier. Displays as a prominent banner in
    phase instructions. All agents spawned in any phase receive the
    guidance.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active"), file=sys.stderr)
        sys.exit(1)

    phase = getattr(args, "phase", "") or state["current_phase"]
    phase = phase.upper()
    clear = getattr(args, "clear", False)
    processed = getattr(args, "processed", False)

    # Clear by identifier
    if clear:
        identifier = (args.message or "").strip()
        if not identifier:
            print(
                "--clear requires an identifier (pass via --message IDENTIFIER)", file=sys.stderr
            )
            sys.exit(1)
        ctx = _load_context()
        if identifier not in ctx:
            print(f"Context identifier '{identifier}' not found.", file=sys.stderr)
            sys.exit(1)
        ctx.pop(identifier)
        _save_context(ctx)
        print(_msg("context_cleared", phase=identifier))
        return

    # Mark processed by identifier
    if processed:
        identifier = (args.message or "").strip()
        if not identifier:
            print(
                "--processed requires an identifier (pass via --message IDENTIFIER)",
                file=sys.stderr,
            )
            sys.exit(1)
        ctx = _load_context()
        if identifier not in ctx:
            print(f"Context identifier '{identifier}' not found.", file=sys.stderr)
            sys.exit(1)
        current_status = ctx[identifier].get("status", "new")
        if "processed" not in _VALID_CONTEXT_TRANSITIONS.get(current_status, set()):
            print(
                f"Cannot transition context '{identifier}' from '{current_status}' to 'processed'.",
                file=sys.stderr,
            )
            sys.exit(1)
        note_text = getattr(args, "note", "") or "marked processed"
        ctx[identifier]["status"] = "processed"
        ctx[identifier].setdefault("notes", []).append({"processed": note_text})
        _save_context(ctx)
        print(f"Context '{identifier}' marked as processed.")
        return

    # Dismiss context entry by identifier
    dismiss = getattr(args, "dismiss", False)
    if dismiss:
        identifier = (args.message or "").strip()
        if not identifier:
            print(
                "--dismiss requires an identifier (pass via --message IDENTIFIER)",
                file=sys.stderr,
            )
            sys.exit(1)
        ctx = _load_context()
        if identifier not in ctx:
            print(f"Context identifier '{identifier}' not found.", file=sys.stderr)
            sys.exit(1)
        current_status = ctx[identifier].get("status", "new")
        if "dismissed" not in _VALID_CONTEXT_TRANSITIONS.get(current_status, set()):
            print(
                f"Cannot transition context '{identifier}' from '{current_status}' to 'dismissed'.",
                file=sys.stderr,
            )
            sys.exit(1)
        note_text = getattr(args, "note", "") or "dismissed"
        ctx[identifier]["status"] = "dismissed"
        ctx[identifier].setdefault("notes", []).append({"dismissed": note_text})
        _save_context(ctx)
        print(f"Context '{identifier}' dismissed.")
        return

    # List all context entries
    message = args.message
    if not message:
        ctx = _load_context()
        if not ctx:
            print(_msg("context_none"))
        else:
            for cid, entry in ctx.items():
                msg = entry.get("message", "")
                p = entry.get("phase", "?")
                status = entry.get("status", "?")
                notes = entry.get("notes", [])
                latest = ""
                if notes:
                    last = notes[-1]
                    latest = next(iter(last.values()), "")
                truncated = msg[:80]
                ellipsis = "..." if len(msg) > 80 else ""
                print(f"  [{cid}] ({p}): {truncated}{ellipsis}  (status: {status}) {latest[:40]}")
        return

    # Add new context entry
    ctx = _load_context()
    cid = _generate_entry_id(message, set(ctx.keys()))
    ctx[cid] = {
        "message": message,
        "phase": phase,
        "created": _now(),
        "status": "new",
        "notes": [],
    }
    _save_context(ctx)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "user_context",
            "identifier": cid,
            "message": message[:200],
        }
    )
    print(_msg("context_set", phase=phase))
    print(f"  identifier: {cid}")
    print(_msg("context_message", message=message))
    if state["phase_status"] == "in_progress" and state["current_phase"] == phase:
        print("\n" + _msg("context_in_progress", cmd=CMD))
    else:
        print("\n" + _msg("context_will_show", phase=phase))


def cmd_log_failure(args) -> None:
    """Log a failure mode found during the iteration.

    Appends to failures.yaml with mode ID, description, iteration,
    phase, and optional context. Failure modes accumulate across
    iterations and feed into RESEARCH phase context for the next iteration.
    """
    state = _load_state()
    iteration = state["iteration"] if state else 0
    phase = state["current_phase"] if state else "unknown"
    context_str = getattr(args, "context", "") or ""
    _append_failure(
        {
            "iteration": iteration,
            "phase": phase,
            "mode": args.mode,
            "description": args.desc,
            "context": context_str,
        }
    )
    print(_msg("failure_logged", mode=args.mode, desc=args.desc))


def cmd_failures(args) -> None:
    """Display the failure log grouped by iteration, or mark as processed.

    Shows all logged failure modes with their identifier, mode ID, phase,
    description, and solution status. Supports --processed to mark a failure
    as addressed and --solution to record the fix.
    """
    processed_id = getattr(args, "processed", "") or ""
    solution_text = getattr(args, "solution", "") or ""

    if processed_id:
        failures = _load_failures()
        if processed_id not in failures:
            print(f"Failure '{processed_id}' not found.", file=sys.stderr)
            sys.exit(1)
        failures[processed_id]["status"] = "processed"
        failures[processed_id].setdefault("notes", []).append(
            {"processed": solution_text or "marked processed"}
        )
        if solution_text:
            failures[processed_id]["solution"] = solution_text
        _save_failures(failures)
        print(f"Failure '{processed_id}' marked as processed.")
        return

    failures = _load_failures()
    if not failures:
        print(_msg("no_failures"))
        return

    by_iter: dict[int, list] = {}
    for fid, e in failures.items():
        it = e.get("iteration", 0)
        by_iter.setdefault(it, []).append((fid, e))

    for it in sorted(by_iter.keys()):
        print("\n" + _msg("failure_iteration_header", iteration=it))
        for fid, e in by_iter[it]:
            mode = e.get("mode", "?")
            desc = e.get("description", "?")
            phase = e.get("phase", "?")
            status = e.get("status", "new")
            solved = e.get("solution")
            status_tag = f" [{status.upper()}]" if status != "new" else ""
            sol = f" SOLUTION: {solved}" if solved else ""
            print(f"  [{fid}] ({mode}) {phase}: {desc[:60]}{status_tag}{sol}")


def cmd_info(args) -> None:
    """Query model information: workflows, phases, agents.

    Reads from the loaded _MODEL to display structured information about
    the orchestration configuration. Supports five query modes via flags:
    --workflows, --workflow <name>, --phases, --phase <name>, --agents.
    """
    if args.workflows:
        # Table: FQN | cli_name | description | phases | agent_count
        print(f"{'FQN':<25} {'cli_name':<12} {'description':<55} {'phases':>6} {'agents':>6}")
        print("-" * 110)
        for fqn, wt in _MODEL.workflow_types.items():
            # Count agents across all phases in this workflow
            prefix = fqn.split("::", 1)[1] if "::" in fqn else fqn
            agent_count = 0
            for phase_name in wt.phase_names:
                # Check namespaced first, then bare
                for key in [f"{prefix}::{phase_name}", phase_name]:
                    if key in _MODEL.agents:
                        agent_count += len(_MODEL.agents[key])
                        break
            print(
                f"{fqn:<25} {wt.cli_name:<12} {wt.description[:55]:<55} "
                f"{len(wt.phase_names):>6} {agent_count:>6}"
            )
        return

    if args.workflow:
        # Find workflow by cli_name
        fqn = _CLI_TO_FQN.get(args.workflow)
        if not fqn:
            print(f"Unknown workflow cli_name: {args.workflow}")
            return
        wt = _MODEL.workflow_types[fqn]
        prefix = fqn.split("::", 1)[1] if "::" in fqn else fqn
        print(f"Workflow: {fqn} (cli_name: {wt.cli_name})")
        print(f"Description: {wt.description}")
        if wt.depends_on:
            print(f"Depends on: {wt.depends_on}")
        print(f"Independent: {wt.independent}")
        print(f"{len(wt.phase_names)} phases:")
        for phase_name in wt.phase_names:
            req = "required" if phase_name in wt.required else "skippable"
            # Resolve agents for this phase
            agents = []
            for key in [f"{prefix}::{phase_name}", phase_name]:
                if key in _MODEL.agents:
                    agents = [a.name for a in _MODEL.agents[key]]
                    break
            # Check depends_on in phase definition
            phase_key = None
            for key in [f"{prefix}::{phase_name}", phase_name]:
                if key in _MODEL.phases:
                    phase_key = key
                    break
            agent_str = f"  agents: {', '.join(agents)}" if agents else ""
            print(f"  {phase_name} ({req}){agent_str}")
        return

    if args.phases:
        # Table: name | start_agents | execution_agents | end_agents
        print(f"{'phase':<25} {'start_agents':<20} {'execution_agents':<30} {'end_agents':<20}")
        print("-" * 100)
        for phase_name in _MODEL.phases:
            # Start agents (gates): find readback etc.
            start_agents = []
            for gk, gv in _MODEL.gates.items():
                if (
                    gk.startswith(f"{phase_name}::")
                    and gk.rsplit("::", 1)[1] in _MODEL.start_gate_types
                ):
                    start_agents.append(gk.rsplit("::", 1)[1])
            # Execution agents
            exec_agents = [a.name for a in _MODEL.agents.get(phase_name, [])]
            # End agents (gates): find gatekeeper etc.
            end_agents = []
            for gk, gv in _MODEL.gates.items():
                if (
                    gk.startswith(f"{phase_name}::")
                    and gk.rsplit("::", 1)[1] in _MODEL.end_gate_types
                ):
                    end_agents.append(gk.rsplit("::", 1)[1])
            print(
                f"{phase_name:<25} {', '.join(start_agents):<20} "
                f"{', '.join(exec_agents):<30} {', '.join(end_agents):<20}"
            )
        return

    if args.phase:
        phase_name = args.phase
        if phase_name not in _MODEL.phases:
            print(f"Unknown phase: {phase_name}")
            return
        phase = _MODEL.phases[phase_name]
        print(f"Phase: {phase_name}")
        # Start agents
        print("  Start agents:")
        for gk, gv in _MODEL.gates.items():
            if (
                gk.startswith(f"{phase_name}::")
                and gk.rsplit("::", 1)[1] in _MODEL.start_gate_types
            ):
                gate_type = gk.rsplit("::", 1)[1]
                prompt_preview = gv.prompt[:100] if gv.prompt else ""
                print(f"    {gate_type}: {prompt_preview}")
        # Execution agents
        exec_agents = _MODEL.agents.get(phase_name, [])
        if exec_agents:
            print("  Execution agents:")
            for a in exec_agents:
                print(f"    {a.name} ({a.display_name})")
        else:
            print("  Execution agents: (none)")
        # End agents
        print("  End agents:")
        for gk, gv in _MODEL.gates.items():
            if gk.startswith(f"{phase_name}::") and gk.rsplit("::", 1)[1] in _MODEL.end_gate_types:
                gate_type = gk.rsplit("::", 1)[1]
                prompt_preview = gv.prompt[:100] if gv.prompt else ""
                print(f"    {gate_type}: {prompt_preview}")
        # Template preview
        if phase.start:
            print(f"  Start template: {phase.start[:100]}")
        if phase.end:
            print(f"  End template: {phase.end[:100]}")
        return

    if args.agents:
        # All agents grouped by phase
        # Execution agents from PHASE_AGENTS
        for phase_key in sorted(_MODEL.phases.keys()):
            agents_info = []
            # Start gate agents
            for gk in sorted(_MODEL.gates.keys()):
                if (
                    gk.startswith(f"{phase_key}::")
                    and gk.rsplit("::", 1)[1] in _MODEL.start_gate_types
                ):
                    agents_info.append(f"{gk.rsplit('::', 1)[1]} (start)")
            # Execution agents
            for a in _MODEL.agents.get(phase_key, []):
                agents_info.append(f"{a.name} (execution)")
            # End gate agents
            for gk in sorted(_MODEL.gates.keys()):
                if (
                    gk.startswith(f"{phase_key}::")
                    and gk.rsplit("::", 1)[1] in _MODEL.end_gate_types
                ):
                    agents_info.append(f"{gk.rsplit('::', 1)[1]} (end)")
            if agents_info:
                print(f"{phase_key}: {', '.join(agents_info)}")
        return

    print("Use --workflows, --workflow <name>, --phases, --phase <name>, or --agents")


def cmd_validate(args) -> None:
    """Run model validation and report any issues found.

    Loads the model from YAML resources, runs validate_model(), and prints
    each issue in human-readable format with file origin, location, and fix
    suggestion. Exits with code 0 if the model is valid, 1 if issues found.
    """
    issues = validate_model(_MODEL)
    if not issues:
        print(_msg("validate_success"))
        sys.exit(0)
    print(_msg("validate_issues", count=len(issues)))
    for i, issue in enumerate(issues, 1):
        print(_msg("validate_item", num=i, issue=issue))
    sys.exit(1)


def _dry_run_phase(workflow: str, phase_name: str) -> list[str]:
    """Print expected agents and gates for one phase. Returns list of issues."""
    issues: list[str] = []
    # workflow is cli_name here, convert to prefix
    wf_prefix = _workflow_prefix(workflow)
    try:
        phase_key = resolve_phase_key(wf_prefix, phase_name, set(_MODEL.phases.keys()))
    except KeyError as e:
        issues.append(str(e))
        phase_key = phase_name
    try:
        agent_key = resolve_phase_key(wf_prefix, phase_name, set(_MODEL.agents.keys()))
    except KeyError:
        agent_key = phase_name
    agents = _MODEL.agents.get(agent_key, [])

    gate_phases = {k.rsplit("::", 1)[0] for k in _MODEL.gates if "::" in k}
    try:
        gate_key = resolve_phase_key(wf_prefix, phase_name, gate_phases)
    except KeyError:
        gate_key = phase_name
    # Check for start/end gates using lifecycle metadata from the model
    has_rb = any(f"{gate_key}::{gt}" in _MODEL.gates for gt in _MODEL.start_gate_types)
    has_gk = any(f"{gate_key}::{gt}" in _MODEL.gates for gt in _MODEL.end_gate_types)

    wf_fqn = _CLI_TO_FQN.get(workflow, workflow)
    skippable = any(
        p.get("skippable") for p in _MODEL.workflow_types[wf_fqn].phases if p["name"] == phase_name
    )
    tag = "skip" if skippable else "req"
    agent_names = ", ".join(a.name for a in agents) if agents else "none"
    rb = "yes" if has_rb else "NO"
    gk = "yes" if has_gk else "NO"

    # Report resolution path
    resolved_display = phase_key if phase_key != phase_name else phase_name
    print(
        _msg("dry_run_phase_line", phase=phase_name, tag=tag, agents=agent_names, rb=rb, gk=gk)
        + f"  [{resolved_display}]"
    )

    # Test template rendering with dummy context
    phase_obj = _MODEL.phases.get(phase_key)
    if phase_obj:
        dummy_ctx = collections.defaultdict(str, {v: f"<{v}>" for v in _KNOWN_TEMPLATE_VARS})
        for attr in ("start", "end", "start_continue", "start_final", "end_continue", "end_final"):
            text = getattr(phase_obj, attr, "")
            if text:
                try:
                    text.format_map(dummy_ctx)
                except (KeyError, ValueError, IndexError) as exc:
                    issues.append(
                        f"[phases.yaml] '{phase_key}.{attr}': template render error: {exc}"
                    )

    return issues


def _dry_run(itype: str, total_iterations: int) -> None:
    """Print expected execution plan without creating state."""
    issues = validate_model(_MODEL)
    if issues:
        for issue in issues:
            print(_msg("dry_run_error", issue=issue))
        sys.exit(1)
    print(_msg("dry_run_valid"))

    wf_fqn = _CLI_TO_FQN.get(itype, itype)
    wf = _MODEL.workflow_types[wf_fqn]
    dep_wf = _MODEL.workflow_types.get(wf.depends_on) if wf.depends_on else None
    template_issues: list[str] = []

    if dep_wf and total_iterations > 1:
        dep_cli = dep_wf.cli_name or wf.depends_on
        print(_msg("dry_run_planning_iter", wtype=dep_cli))
        for p in dep_wf.phases:
            template_issues.extend(_dry_run_phase(dep_cli, p["name"]))

    for i in range(1, total_iterations + 1):
        print(_msg("dry_run_impl_iter", num=i, wtype=itype))
        for p in wf.phases:
            template_issues.extend(_dry_run_phase(itype, p["name"]))

    if template_issues:
        print("\n  Template rendering issues:")
        for ti in template_issues:
            print(f"    {ti}")
        sys.exit(1)

    # FSM lifecycle simulation - verify all transitions work
    if dep_wf and total_iterations > 1:
        dep_reports = _PHASE_FSM.simulate([p["name"] for p in dep_wf.phases])
        for r in dep_reports:
            if not r["valid"]:
                print(
                    _msg(
                        "dry_run_error",
                        issue=f"FSM simulation failed for {r['phase']}: {r.get('error', '')}",
                    )
                )
                sys.exit(1)

    reports = _PHASE_FSM.simulate([p["name"] for p in wf.phases])
    for r in reports:
        if not r["valid"]:
            print(
                _msg(
                    "dry_run_error",
                    issue=f"FSM simulation failed for {r['phase']}: {r.get('error', '')}",
                )
            )
            sys.exit(1)

    print(_msg("dry_run_complete"))


def cmd_add_iteration(args) -> None:
    """Add iterations to an active cycle without restarting."""
    state = _load_state()
    if not state:
        print(_msg("no_active_add_iteration"), file=sys.stderr)
        sys.exit(1)
    count = args.count
    old_total = state["total_iterations"]
    state["total_iterations"] = old_total + count
    new_objective = getattr(args, "objective", "") or ""
    if new_objective:
        state["objective"] = new_objective
    _save_state(state)
    _append_log(
        {
            "iteration": state["iteration"],
            "event": "add_iteration",
            "count": count,
            "old_total": old_total,
            "new_total": old_total + count,
        }
    )
    print(_msg("add_iteration_success", count=count, old=old_total, new=old_total + count))


# ── Main ─────────────────────────────────────────────────────────────


def _build_cli_parser(resources_dir: Path) -> argparse.ArgumentParser:
    """Build the argparse parser with all subcommands and arguments."""
    parser = argparse.ArgumentParser(
        description=_cli("description", ""),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_cli("epilog", ""),
    )
    parser.add_argument(
        "--resources-dir",
        default=str(resources_dir),
        help="Path to YAML resource files directory",
    )
    parser.add_argument(
        "--no-version-check",
        action="store_true",
        default=False,
        help="Skip PyPI version check on startup",
    )
    sub = parser.add_subparsers(dest="command")

    # ── new ──
    p_new = sub.add_parser("new", help=_cli("commands", "new"))
    p_new.add_argument(
        "--type",
        required=True,
        choices=list(ITERATION_TYPES.keys()),
    )
    p_new.add_argument("--objective", required=True, help=_cli("args", "objective"))
    p_new.add_argument("--iterations", type=int, default=1, help=_cli("args", "iterations"))
    p_new.add_argument("--benchmark", default="", help=_cli("args", "benchmark"))
    p_new.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        default=False,
        help=_cli("args", "continue_session"),
    )
    p_new.add_argument(
        "--restart",
        dest="restart_session",
        action="store_true",
        default=False,
        help="Restart current iteration from beginning (optionally update objective/benchmark/iterations)",
    )
    p_new.add_argument(
        "--dry-run", action="store_true", default=False, help=_cli("args", "dry_run")
    )
    p_new.add_argument(
        "--record-instructions",
        default="",
        help="Custom instructions for RECORD phase (e.g. journal, git push)",
    )

    # ── start ──
    p_start = sub.add_parser("start", help=_cli("commands", "start"))
    p_start.add_argument("--understanding", required=True, help=_cli("args", "understanding"))

    # ── end ──
    p_end = sub.add_parser("end", help=_cli("commands", "end"))
    p_end.add_argument("--evidence", default="", help=_cli("args", "evidence"))
    p_end.add_argument("--agents", default="", help=_cli("args", "agents"))
    p_end.add_argument("--output-file", default="", help=_cli("args", "output_file"))

    # ── status ──
    sub.add_parser("status", help=_cli("commands", "status"))

    # ── reject ──
    p_reject = sub.add_parser("reject", help=_cli("commands", "reject"))
    p_reject.add_argument("--reason", required=True, help=_cli("args", "reason"))

    # ── skip ──
    p_skip = sub.add_parser("skip", help=_cli("commands", "skip"))
    p_skip.add_argument("--reason", default="", help=_cli("args", "skip_reason"))
    p_skip.add_argument("--force", action="store_true", default=False, help=_cli("args", "force"))

    # ── context ──
    p_ctx = sub.add_parser("context", help=_cli("commands", "context"))
    p_ctx.add_argument("--message", default="", help=_cli("args", "message"))
    p_ctx.add_argument("--phase", default="", help=_cli("args", "phase"))
    p_ctx.add_argument("--clear", action="store_true", default=False, help=_cli("args", "clear"))
    p_ctx.add_argument(
        "--processed",
        action="store_true",
        default=False,
        help="Mark context entry as processed (pass identifier via --message)",
    )
    p_ctx.add_argument(
        "--dismiss",
        action="store_true",
        default=False,
        help="Dismiss context entry (pass identifier via --message)",
    )
    p_ctx.add_argument(
        "--note",
        default="",
        help="Note for --processed or --dismiss transitions",
    )

    # ── log-failure ──
    p_fail = sub.add_parser("log-failure", help=_cli("commands", "log_failure"))
    p_fail.add_argument("--mode", required=True, help=_cli("args", "mode"))
    p_fail.add_argument("--desc", required=True, help=_cli("args", "desc"))
    p_fail.add_argument("--context", default="", help="Context of when failure occurred")

    # ── failures ──
    p_failures = sub.add_parser("failures", help=_cli("commands", "failures"))
    p_failures.add_argument(
        "--processed", default="", help="Mark failure as processed (pass identifier)"
    )
    p_failures.add_argument(
        "--solution", default="", help="Solution description (use with --processed)"
    )

    # ── add-iteration ──
    p_add = sub.add_parser("add-iteration", help=_cli("commands", "add_iteration"))
    p_add.add_argument("--count", type=int, required=True, help=_cli("args", "count"))
    p_add.add_argument("--objective", default="", help=_cli("args", "add_objective"))

    # ── info ──
    p_info = sub.add_parser("info", help="Query model information")
    p_info.add_argument("--workflows", action="store_true")
    p_info.add_argument("--workflow", type=str)
    p_info.add_argument("--phases", action="store_true")
    p_info.add_argument("--phase", type=str)
    p_info.add_argument("--agents", action="store_true")

    # ── validate ──
    sub.add_parser("validate", help="Validate YAML resources against the model schema")

    return parser


_BUNDLED_RESOURCES = Path(__file__).parent / "resources"
_RESOURCE_FILES = ("workflow.yaml", "phases.yaml", "app.yaml")


def _detect_stale_resources(resources_dir: Path) -> bool:
    """Check if project resources are stale (old format or differ from bundled).

    Detects two cases:
    1. Legacy gates: format (pre-start/execution/end lifecycle)
    2. Content differs from bundled resources (version upgrade)
    """
    phases_file = resources_dir / "phases.yaml"
    if not phases_file.exists():
        return False
    content = phases_file.read_text()
    # Old format: gates: key at phase level without start: key
    if "  gates:" in content and "  start:" not in content:
        return True
    # Version upgrade: bundled resources differ from project-local
    for fname in _RESOURCE_FILES:
        local = resources_dir / fname
        bundled = _BUNDLED_RESOURCES / fname
        if local.exists() and bundled.exists():
            if local.read_bytes() != bundled.read_bytes():
                return True
    return False


def _ensure_project_resources(project_resources: Path) -> Path:
    """Ensure project-local resources exist, copying defaults from module if needed.

    Returns the project resources directory path. If any YAML file is missing,
    copies the default from the module's bundled resources. Detects and archives
    stale resources (old format or version mismatch).
    """
    project_resources.mkdir(parents=True, exist_ok=True)
    for fname in _RESOURCE_FILES:
        dest = project_resources / fname
        if not dest.exists():
            src = _BUNDLED_RESOURCES / fname
            if src.exists():
                shutil.copy2(src, dest)

    # Detect and archive stale resources (old format or version upgrade)
    if _detect_stale_resources(project_resources):
        archive_name = f"resources.old.{datetime.now().strftime('%Y%m%d')}"
        archive_path = project_resources.parent / archive_name
        if not archive_path.exists():
            project_resources.rename(archive_path)
            print(
                f"WARNING: Project resources differ from bundled version. "
                f"Archived to {archive_name}/"
            )
            project_resources.mkdir(parents=True, exist_ok=True)
            for fname in _RESOURCE_FILES:
                src = _BUNDLED_RESOURCES / fname
                if src.exists():
                    shutil.copy2(src, project_resources / fname)
            print("Fresh resources installed from module.")

    return project_resources


def _check_version() -> None:
    """Check if a newer version is available on PyPI. Non-blocking, 2s timeout.

    Cache stored as YAML: {latest_version: str, checked_at: ISO8601}.
    Uses checked_at for 24h expiry instead of file mtime.
    Legacy plain-text cache is silently migrated on next check.
    """
    try:
        import importlib.metadata
        import json
        from urllib.request import urlopen

        installed = importlib.metadata.version("stellars-claude-code-plugins")

        # Check cache - structured YAML with checked_at timestamp
        cache_file = PROJECT_ROOT / ".auto-build-claw" / ".version_check"
        if cache_file.exists():
            cache_data = yaml.safe_load(cache_file.read_text())
            if isinstance(cache_data, dict) and "checked_at" in cache_data:
                checked = datetime.fromisoformat(cache_data["checked_at"])
                if (datetime.now(timezone.utc) - checked).total_seconds() < 86400:
                    return

        url = "https://pypi.org/pypi/stellars-claude-code-plugins/json"
        resp = urlopen(url, timeout=2)  # noqa: S310
        data = json.loads(resp.read())
        latest = data["info"]["version"]

        # Update cache as structured YAML
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(yaml.dump({"latest_version": latest, "checked_at": _now()}))

        if latest != installed:
            print(
                f"Update available: {installed} -> {latest}. "
                f"Run: pip install --upgrade stellars-claude-code-plugins"
            )
    except Exception:
        pass  # Fail silently


def main(resources_dir: Path | None = None):
    """CLI entry point. Parses arguments and dispatches to command handlers.

    Args:
        resources_dir: Path to YAML resource files directory. If None,
            uses resolution chain: --resources-dir CLI arg > project-local
            resources > bundled module resources.
    """
    # Version check (before _initialize, non-blocking)
    no_version_check = "--no-version-check" in sys.argv
    if not no_version_check:
        _check_version()

    # Resolve resources_dir: explicit arg > CLI --resources-dir > project-local > bundled
    if resources_dir is None:
        # Pre-parse --resources-dir before full argparse (it needs _initialize first)
        for i, arg in enumerate(sys.argv[1:]):
            if arg == "--resources-dir" and i + 1 < len(sys.argv) - 1:
                resources_dir = Path(sys.argv[i + 2])
                break
            if arg.startswith("--resources-dir="):
                resources_dir = Path(arg.split("=", 1)[1])
                break
    if resources_dir is None:
        # Try project-local resources first, copy defaults if missing
        project_resources = PROJECT_ROOT / ".auto-build-claw" / "resources"
        if _BUNDLED_RESOURCES.exists():
            resources_dir = _ensure_project_resources(project_resources)
        elif project_resources.exists():
            resources_dir = project_resources
        else:
            resources_dir = _BUNDLED_RESOURCES

    _initialize(resources_dir)

    parser = _build_cli_parser(resources_dir)
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize artifacts directory
    _init_artifacts_dir()

    cmds = {
        "new": cmd_new,
        "start": cmd_start,
        "end": cmd_end,
        "status": cmd_status,
        "reject": cmd_reject,
        "skip": cmd_skip,
        "context": cmd_context,
        "log-failure": cmd_log_failure,
        "failures": cmd_failures,
        "add-iteration": cmd_add_iteration,
        "info": cmd_info,
        "validate": cmd_validate,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
