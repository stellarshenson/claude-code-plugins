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
import subprocess
import sys

import yaml

from stellars_claude_code_plugins.engine.fsm import (
    Event as FSMEvent,
)
from stellars_claude_code_plugins.engine.fsm import (
    State as FSMState,
)
from stellars_claude_code_plugins.engine.fsm import (
    build_phase_lifecycle_fsm,
    resolve_phase_key,
)
from stellars_claude_code_plugins.engine.model import (
    _KNOWN_VARS as _KNOWN_TEMPLATE_VARS,
)
from stellars_claude_code_plugins.engine.model import (
    _resolve_key,
    load_model,
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
    global ITERATION_TYPES, PHASE_AGENTS, _PHASE_START, _PHASE_END
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
    _FSM_STATE_VALUES = {s.value for s in FSMState}

    # Build ITERATION_TYPES from model.workflow_types
    ITERATION_TYPES.clear()
    ITERATION_TYPES.update(
        {
            name: {
                "description": wt.description,
                "phases": wt.phase_names,
                "required": wt.required,
                "skippable": wt.skippable,
            }
            for name, wt in _MODEL.workflow_types.items()
        }
    )

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


def _fire_fsm(event: FSMEvent, state: dict) -> FSMState:
    """Fire FSM event and sync phase_status to state dict.

    Syncs FSM from persisted state before firing, then writes back.
    All phase_status mutations go through this function.
    """
    status = state.get("phase_status", "pending")
    _PHASE_FSM.current_state = (
        FSMState(status) if status in _FSM_STATE_VALUES else FSMState.PENDING
    )
    new_state = _PHASE_FSM.fire(event)
    state["phase_status"] = new_state.value
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
            if agent.name == "guardian" and agent.checklist:
                return agent.checklist
    return ""


def _current_workflow_type() -> str:
    """Get current workflow type from state, defaulting to 'full'."""
    state = _load_state()
    return (state or {}).get("type", "full")


def _resolve_phase(phase: str) -> str:
    """Resolve a phase name to its namespaced key in phases.yaml."""
    return resolve_phase_key(_current_workflow_type(), phase, _MODEL.phases)


def _resolve_agents(phase: str) -> str:
    """Resolve a phase name to its namespaced key in agents.yaml."""
    return resolve_phase_key(_current_workflow_type(), phase, _MODEL.agents)


def _resolve_gate(phase: str, gate_type: str) -> str:
    """Resolve a gate key for a phase using the :: fallback chain.

    Gate keys are namespaced: FULL::RESEARCH::readback, FULL::TEST::gatekeeper.
    Resolution follows the same WORKFLOW::PHASE -> PHASE -> FULL::PHASE chain.
    """
    gate_phases = {
        k.rsplit("::", 1)[0]
        for k in _MODEL.gates
        if "::" in k and k.rsplit("::", 1)[1] == gate_type
    }
    resolved = _resolve_key(_current_workflow_type(), phase, gate_phases)
    return f"{resolved}::{gate_type}"


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
    for agent in agents:
        prompt = agent.prompt
        checklist = agent.checklist or ""
        # Append checklist to prompt if agent has one
        if checklist:
            prompt = prompt.rstrip() + "\n\n" + checklist
        # Resolve any template variables in the prompt (e.g., {checklist})
        if ctx and "{" in prompt:
            prompt = prompt.format_map(collections.defaultdict(str, ctx))
        lines.append(f"### Agent {agent.number}: {agent.display_name}")
        lines.append(prompt.rstrip())
        lines.append("")
    return "\n".join(lines).rstrip()


# ── Build context for template rendering ────────────────────────────


def _build_failures_context() -> str:
    """Build prior failures context string from failures.yaml."""
    all_failures = _load_yaml_list(FAILURES_FILE)
    if not all_failures:
        return ""
    prior_context = f"\n**Prior failures** ({len(all_failures)} total):\n"
    for f in all_failures[-5:]:
        prior_context += (
            f"  - [{f.get('mode', '?')}] "
            f"(iter {f.get('iteration', '?')}) "
            f"{f.get('description', '?')}\n"
        )
    return prior_context


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
    instructions from agents.yaml.

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
    itype = s.get("type", "full")
    iteration_plan = s.get("iteration_plan", "")
    wf_def = _MODEL.workflow_types.get(itype)
    if wf_def and not wf_def.independent:
        iteration_purpose = "\n" + _msg("dependency_banner", description=wf_def.description) + "\n"
    elif iteration > 0 and iteration_plan:
        iteration_purpose = (
            "\n" + _msg("iteration_n_banner", iteration=iteration, total=total_iters) + "\n"
        )
    else:
        iteration_purpose = ""

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
        # Handle conditional templates (NEXT has remaining/final variants)
        key = event
        if phase == "NEXT":
            remaining = ctx["remaining"]
            if event == "start":
                key = "start_continue" if remaining > 0 else "start_final"
            elif event == "end":
                key = "end_continue" if remaining > 0 else "end_final"
        resolved_phase = _resolve_phase(phase)
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
    if nxt == "NEXT":
        print("\n" + _msg("auto_separator"))
        print(_msg("auto_next"))
        print(_msg("auto_autonomous"))
        print(_msg("auto_separator"))
        next_instructions = _PHASE_START.get("NEXT", lambda: "")()
        print(next_instructions)


def _action_iteration_advance(state: dict, phase: str):
    _run_next_iteration(state)
    return "return"


def _action_plan_save(state: dict, phase: str):
    """Save PLAN output as plan.yaml for dependency workflows."""
    wf_def = _MODEL.workflow_types.get(state.get("type", ""))
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
    """Run auto_actions.on_complete for the resolved phase. Returns True if handler signalled early return."""
    resolved = _resolve_phase(phase)
    phase_obj = _MODEL.phases.get(resolved)
    if not phase_obj or not phase_obj.auto_actions:
        return False
    actions = phase_obj.auto_actions.get("on_complete", [])
    for action_name in actions:
        handler = _AUTO_ACTION_REGISTRY.get(action_name)
        if handler:
            result = handler(state, phase)
            if result == "return":
                return True
    return False


# ── Helper functions ─────────────────────────────────────────────────


def _now() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_state() -> dict | None:
    """Load iteration state from state.yaml."""
    if STATE_FILE.exists():
        return yaml.safe_load(STATE_FILE.read_text())
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
    """Append a timestamped failure entry to the failures log."""
    entry["timestamp"] = _now()
    _append_yaml_entry(FAILURES_FILE, entry)


def _load_context() -> dict:
    """Load context messages from context.yaml.

    Returns a dict mapping phase names to message strings. Returns empty
    dict if file doesn't exist (first run or never set).
    """
    if not CONTEXT_FILE.exists():
        return {}
    data = yaml.safe_load(CONTEXT_FILE.read_text())
    return data if isinstance(data, dict) else {}


def _save_context(ctx: dict) -> None:
    """Save context messages to context.yaml."""
    CONTEXT_FILE.write_text(_yaml_dump(ctx))


def _phase_dir(state: dict) -> Path:
    """Get/create phase artifacts subfolder: phase_N_NAME/."""
    itype = ITERATION_TYPES[state["type"]]
    phases = itype["phases"]
    phase = state["current_phase"]
    idx = phases.index(phase) + 1 if phase in phases else 0
    folder = DEFAULT_ARTIFACTS_DIR / f"phase_{idx:02d}_{phase.lower()}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


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

    Walks backward through the phase sequence looking for IMPLEMENT.
    Used by cmd_reject and the TEST auto-reject to determine which
    phase to roll back to.
    """
    itype = ITERATION_TYPES[state["type"]]
    phases = itype["phases"]
    idx = phases.index(state["current_phase"])
    for i in range(idx - 1, -1, -1):
        if phases[i] == "IMPLEMENT":
            return "IMPLEMENT"
    return phases[0]


def _count_iteration_failures(iteration: int) -> list[dict]:
    """Read failure log entries for a specific iteration."""
    return [e for e in _load_yaml_list(FAILURES_FILE) if e.get("iteration") == iteration]


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


def _clean_artifacts_dir(artifacts_dir: Path | None = None) -> None:
    """Clean artifacts directory for fresh run.

    Preserves context.yaml across clean operations.
    """
    d = artifacts_dir or DEFAULT_ARTIFACTS_DIR
    if d.exists():
        for f in d.iterdir():
            if f.is_file():
                # Preserve context files across clean
                if f.name == "context.yaml":
                    continue
                f.unlink()
            elif f.is_dir():
                import shutil

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
        results.append("  INSTRUCTION: Read the benchmark file, evaluate each [ ] item,")
        results.append("  update [ ] -> [x] for passing items, add new [ ] items if discovered,")
        results.append("  then report the count of remaining [ ] items as the violation score.")
        results.append("  The orchestrating agent MUST follow this instruction before proceeding.")

    return True, "\n".join(results)


# ── Claude evaluation ────────────────────────────────────────────────


def _claude_evaluate(
    prompt: str,
    timeout: int = 60,
) -> tuple[bool, str]:
    """Run claude -p with a PASS/FAIL evaluation prompt.

    Used by readback and gatekeeper gates for independent validation.
    Strips the CLAUDECODE environment variable to prevent subprocess
    hang (claude-agent-sdk detects it and enters degraded mode).
    Uses sonnet model with max-turns 3 and 60s timeout.
    Logs every prompt+response to artifacts/logs/ for debugging.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

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
    except subprocess.TimeoutExpired:
        passed, output = False, f"FAIL: claude -p timed out ({timeout}s)."

    # Log for tracing
    log_dir = DEFAULT_ARTIFACTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
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
    Prompt template loaded from agents.yaml gates.readback.
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
    gate_key = _resolve_gate(phase, "readback")
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
    Prompt template loaded from agents.yaml gates.gatekeeper.
    """
    agents = state.get("phase_agents", {}).get(phase, [])
    output = state.get("phase_outputs", {}).get(phase, "")
    readback = state.get("readbacks", {}).get(phase, {})
    agent_key = _resolve_agents(phase)
    required_agents = PHASE_AGENTS.get(agent_key, [])

    exit_fn = _PHASE_END.get(phase)
    exit_criteria = exit_fn() if exit_fn else f"No exit criteria defined for {phase}"

    gate_key = _resolve_gate(phase, "gatekeeper")
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

    gate_template = _MODEL.gates.get("gatekeeper_skip", None)
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

    gate_template = _MODEL.gates.get("gatekeeper_force_skip", None)
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
    wf_def = _MODEL.workflow_types.get(itype)
    if wf_def and not wf_def.independent:
        iter_label = itype.upper()
    elif total_iters == 0:
        iter_label = f"benchmark-driven {iteration}"
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

    if "RESEARCH" in outputs:
        lines.append("## Research Findings")
        lines.append("")
        for line in outputs["RESEARCH"].split("\n"):
            if line.strip() and not line.startswith(("#", "-", "|")):
                lines.append(f"{line}<br>")
            else:
                lines.append(line)
        lines.append("")

    if "HYPOTHESIS" in outputs:
        lines.append("## Hypotheses")
        lines.append("")
        for line in outputs["HYPOTHESIS"].split("\n"):
            if line.strip() and not line.startswith(("#", "-", "|")):
                lines.append(f"{line}<br>")
            else:
                lines.append(line)
        lines.append("")

    if "PLAN" in outputs:
        lines.append("## Plan")
        lines.append("")
        for line in outputs["PLAN"].split("\n"):
            if line.strip() and not line.startswith(("#", "-", "|")):
                lines.append(f"{line}<br>")
            else:
                lines.append(line)
        lines.append("")

    for phase_name in ["IMPLEMENT", "TEST", "REVIEW"]:
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
        for f in failures:
            lines.append(f"- [{f.get('mode', '?')}] {f.get('description', '?')}")
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
            print("Benchmark conditions met - all iterations complete.")
            return
        if current >= 20:
            print("\nWARNING: 20 iterations without benchmark completion. Pausing.")
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
        wf_def = _MODEL.workflow_types.get(state["type"])
        if wf_def and not wf_def.independent:
            state["type"] = parent
            state.pop("parent_type", None)

    itype_info = ITERATION_TYPES[state["type"]]
    first_phase = itype_info["phases"][0]

    # Preserve iteration_plan from iteration 0
    iteration_plan = state.get("iteration_plan", "") or state.get("phase_outputs", {}).get(
        "PLAN", ""
    )

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
        for f in prior_failures[-3:]:
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
    Cleans prior artifacts by default.
    """
    itype = args.type
    if itype not in ITERATION_TYPES:
        print(
            f"Unknown type: {itype}. Choose: {', '.join(ITERATION_TYPES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Block dependency workflows from direct invocation
    wf_def = _MODEL.workflow_types.get(itype)
    if wf_def and not wf_def.independent:
        print(_msg("dependency_blocked", itype=itype), file=sys.stderr)
        sys.exit(1)

    total_iterations = getattr(args, "iterations", 1)

    # --dry-run: validate and print execution plan, no state files
    if getattr(args, "dry_run", False):
        _dry_run(itype, total_iterations)
        return

    # Read iteration counter BEFORE cleaning (clean wipes state file)
    last_iteration = _read_last_iteration()

    # Clean artifacts from prior runs (default: yes)
    if getattr(args, "clean", True):
        _clean_artifacts_dir()
        print(_msg("cleaned") + "\n")

    old_state = _load_state()
    iteration = max(
        (old_state["iteration"] + 1) if old_state else 1,
        last_iteration + 1,
    )

    # Auto-run dependency workflow (iteration 0) when configured
    run_type = itype
    if wf_def and wf_def.depends_on and total_iterations > 1:
        dep_wf = _MODEL.workflow_types.get(wf_def.depends_on)
        if dep_wf:
            iteration = 0
            run_type = wf_def.depends_on

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
        "benchmark_scores": [],
        "current_phase": first_phase,
        "phase_status": "pending",
        "completed_phases": [],
        "skipped_phases": [],
        "rejected_count": 0,
        "started_at": _now(),
        "phase_outputs": {},
        "phase_agents": {},
        "parent_type": itype if run_type != itype else "",
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

    run_wf = _MODEL.workflow_types.get(run_type)
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
            for f in prior_failures[-3:]:
                print(
                    _msg(
                        "prior_failure_item_full",
                        mode=f.get("mode", "?"),
                        description=f.get("description", "?"),
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
        _fire_fsm(FSMEvent.START, state)  # pending -> readback
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
        _fire_fsm(FSMEvent.READBACK_FAIL, state)  # readback -> pending
        _save_state(state)
        print("\n" + _msg("readback_fail", phase=phase))
        print(_msg("readback_fail_reason", reason=explanation[:200]))
        print("\n" + _msg("readback_retry", cmd=CMD))
        return

    print(_msg("readback_pass", phase=phase) + "\n")

    # Readback passed - advance to in_progress via FSM
    _fire_fsm(FSMEvent.READBACK_PASS, state)  # readback -> in_progress
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
        count = len(all_ctx)
        body += f"\n\n{count} context message(s) active:\n"
        body += _msg("user_guidance_header_line") + "\n"
        body += _msg("user_guidance_header") + "\n"
        body += _msg("user_guidance_header_line") + "\n\n"
        for ctx_phase, ctx_msg in all_ctx.items():
            body += f"**[{ctx_phase}]**: {ctx_msg}\n\n"
        body += _msg("user_guidance_instruction")

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
        output_file_path = Path(output_file_str).resolve()
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

        # Also save to phase subfolder
        pdir = _phase_dir(state)
        output_dest = pdir / "output.md"
        md_lines = []
        for line in output_content.split("\n"):
            if (
                line.strip()
                and not line.startswith("#")
                and not line.startswith("-")
                and not line.startswith("|")
            ):
                md_lines.append(line + "<br>")
            else:
                md_lines.append(line)
        md_content = "\n".join(md_lines)
        output_dest.write_text(
            f"# {phase} Output\n\n{md_content}\n",
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
    _fire_fsm(FSMEvent.END, state)  # in_progress -> gatekeeper
    _fire_fsm(FSMEvent.GATE_FAIL, state)  # gatekeeper -> in_progress
    _fire_fsm(FSMEvent.REJECT, state)  # in_progress -> rejected
    _fire_fsm(FSMEvent.ADVANCE, state)  # rejected -> pending
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
    _fire_fsm(FSMEvent.END, state)  # in_progress -> gatekeeper
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
        _fire_fsm(FSMEvent.GATE_FAIL, state)  # gatekeeper -> in_progress (retry)
        _save_state(state)
        print("\n" + _msg("gatekeeper_fail", phase=phase))
        print(_msg("gatekeeper_fail_reason", reason=gk_output[:300]))
        print("\n" + _msg("gatekeeper_fail_retry", cmd=CMD))

    return gk_passed, gk_output


def _advance_phase(state: dict, phase: str) -> None:
    """Mark phase complete, advance FSM to next phase or iteration_complete."""
    _fire_fsm(FSMEvent.GATE_PASS, state)  # gatekeeper -> complete
    print(_msg("gatekeeper_pass", phase=phase))

    state["completed_phases"].append(phase)
    started_at = state.get("phase_started_at", "")

    nxt = _next_phase(state)
    if nxt:
        _fire_fsm(FSMEvent.ADVANCE, state)  # complete -> pending
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


def cmd_end(args) -> None:
    """Complete current phase with gatekeeper validation.

    Validates --agents against required agents from agents.yaml,
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

    # ── TEST phase: run automated verification ──
    if phase == "TEST":
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

    wf_def = _MODEL.workflow_types.get(wf_type)
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
        for f in failures:
            print(
                _msg(
                    "status_failure_item",
                    mode=f.get("mode", "?"),
                    desc=f.get("description", "?")[:60],
                )
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
    _fire_fsm(FSMEvent.REJECT, state)  # in_progress -> rejected
    _fire_fsm(FSMEvent.ADVANCE, state)  # rejected -> pending
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
    _fire_fsm(FSMEvent.SKIP, state)  # pending -> skipped
    nxt = _next_phase(state)
    if nxt:
        _fire_fsm(FSMEvent.ADVANCE, state)  # skipped -> pending
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

    Stores the user's message in context.yaml (persistent across --clean).
    Displays as a prominent banner in phase instructions. All agents
    spawned in any phase receive the guidance. Can target a specific
    phase or the current one.
    """
    state = _load_state()
    if not state:
        print(_msg("no_active"), file=sys.stderr)
        sys.exit(1)

    phase = getattr(args, "phase", "") or state["current_phase"]
    phase = phase.upper()
    clear = getattr(args, "clear", False)

    if clear:
        ctx = _load_context()
        ctx.pop(phase, None)
        _save_context(ctx)
        print(_msg("context_cleared", phase=phase))
        return

    message = args.message
    if not message:
        ctx = _load_context()
        if not ctx:
            print(_msg("context_none"))
        else:
            for p, msg in ctx.items():
                truncated = msg[:100]
                ellipsis = "..." if len(msg) > 100 else ""
                print(_msg("context_item", phase=p, text=truncated + ellipsis))
        return

    ctx = _load_context()
    ctx[phase] = message
    _save_context(ctx)
    _append_log(
        {
            "iteration": state["iteration"],
            "phase": phase,
            "event": "user_context",
            "message": message[:200],
        }
    )
    print(_msg("context_set", phase=phase))
    print(_msg("context_message", message=message))
    if state["phase_status"] == "in_progress" and state["current_phase"] == phase:
        print("\n" + _msg("context_in_progress", cmd=CMD))
    else:
        print("\n" + _msg("context_will_show", phase=phase))


def cmd_log_failure(args) -> None:
    """Log a failure mode found during the iteration.

    Appends to failures.yaml with mode ID, description, iteration,
    and phase. Failure modes accumulate across iterations and feed
    into RESEARCH phase context for the next iteration.
    """
    state = _load_state()
    iteration = state["iteration"] if state else 0
    phase = state["current_phase"] if state else "unknown"

    _append_failure(
        {
            "iteration": iteration,
            "phase": phase,
            "mode": args.mode,
            "description": args.desc,
        }
    )
    print(_msg("failure_logged", mode=args.mode, desc=args.desc))


def cmd_failures(args) -> None:
    """Display the failure log grouped by iteration.

    Shows all logged failure modes with their mode ID, phase,
    description, and timestamp. Used to review what went wrong
    across iterations.
    """
    if not FAILURES_FILE.exists():
        print(_msg("no_failures"))
        return

    entries = _load_yaml_list(FAILURES_FILE)

    if not entries:
        print(_msg("no_failures"))
        return

    by_iter: dict[int, list] = {}
    for e in entries:
        it = e.get("iteration", 0)
        by_iter.setdefault(it, []).append(e)

    for it in sorted(by_iter.keys()):
        print("\n" + _msg("failure_iteration_header", iteration=it))
        for e in by_iter[it]:
            mode = e.get("mode", "?")
            desc = e.get("description", "?")
            phase = e.get("phase", "?")
            ts = e.get("timestamp", "?")
            print(_msg("failure_item", mode=mode, phase=phase, desc=desc, ts=ts))


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
    phase_key = _resolve_key(workflow, phase_name, set(_MODEL.phases.keys()))
    agent_key = _resolve_key(workflow, phase_name, set(_MODEL.agents.keys()))
    agents = _MODEL.agents.get(agent_key, [])

    gate_phases = {k.rsplit("::", 1)[0] for k in _MODEL.gates if "::" in k}
    gate_key = _resolve_key(workflow, phase_name, gate_phases)
    has_rb = f"{gate_key}::readback" in _MODEL.gates
    has_gk = f"{gate_key}::gatekeeper" in _MODEL.gates

    skippable = any(
        p.get("skippable")
        for p in _MODEL.workflow_types[workflow].phases
        if p["name"] == phase_name
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

    wf = _MODEL.workflow_types[itype]
    dep_wf = _MODEL.workflow_types.get(wf.depends_on) if wf.depends_on else None
    template_issues: list[str] = []

    if dep_wf and total_iterations > 1:
        print(_msg("dry_run_planning_iter", wtype=wf.depends_on))
        for p in dep_wf.phases:
            template_issues.extend(_dry_run_phase(wf.depends_on, p["name"]))

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
    p_new.add_argument("--clean", action="store_true", default=True, help=_cli("args", "clean"))
    p_new.add_argument(
        "--no-clean", action="store_false", dest="clean", help=_cli("args", "no_clean")
    )
    p_new.add_argument(
        "--dry-run", action="store_true", default=False, help=_cli("args", "dry_run")
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

    # ── log-failure ──
    p_fail = sub.add_parser("log-failure", help=_cli("commands", "log_failure"))
    p_fail.add_argument("--mode", required=True, help=_cli("args", "mode"))
    p_fail.add_argument("--desc", required=True, help=_cli("args", "desc"))

    # ── failures ──
    sub.add_parser("failures", help=_cli("commands", "failures"))

    # ── add-iteration ──
    p_add = sub.add_parser("add-iteration", help=_cli("commands", "add_iteration"))
    p_add.add_argument("--count", type=int, required=True, help=_cli("args", "count"))
    p_add.add_argument("--objective", default="", help=_cli("args", "add_objective"))

    # ── validate ──
    sub.add_parser("validate", help="Validate YAML resources against the model schema")

    return parser


def main(resources_dir: Path | None = None):
    """CLI entry point. Parses arguments and dispatches to command handlers.

    Args:
        resources_dir: Path to YAML resource files directory. If None,
            checks --resources-dir CLI argument, then falls back to
            a 'resources' subdirectory next to this file.
    """
    # Resolve resources_dir: explicit arg > CLI --resources-dir > default
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
        resources_dir = Path(__file__).parent / "resources"

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
        "validate": cmd_validate,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
