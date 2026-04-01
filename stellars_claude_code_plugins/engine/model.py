"""Typed object model for auto-build-claw. Loads from 3 YAML resource files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Optional

import yaml


@dataclass
class Agent:
    name: str
    display_name: str
    prompt: str
    mode: str = ""  # "" = parallel via Agent tool; "standalone_session" = claude -p
    checklist: Optional[str] = None


@dataclass
class Gate:
    mode: str
    description: str
    prompt: str  # template with {variable} placeholders


@dataclass
class ActionDef:
    type: str  # "programmatic" or "generative"
    description: str
    prompt: str = ""  # only for generative actions
    cli_name: str = ""  # short name for phases.yaml auto_actions references


@dataclass
class Phase:
    start: str = ""
    end: str = ""
    start_continue: str = ""  # NEXT non-final variant
    start_final: str = ""  # NEXT final variant
    end_continue: str = ""
    end_final: str = ""
    reject_to: Optional[dict] = None  # {phase: str, condition: str} - backward transition target
    auto_actions: Optional[dict] = (
        None  # {on_complete: [action_name, ...]} - actions after phase completes
    )
    auto_verify: bool = False  # if True, run programmatic verification (make test/lint) on end


@dataclass
class WorkflowType:
    description: str
    phases: list[dict]  # raw list [{name: X, skippable?: bool}]
    cli_name: str = ""  # short name for --type flag (e.g., "full" for WORKFLOW::FULL)
    depends_on: str = ""  # prerequisite workflow FQN (e.g., WORKFLOW::PLANNING)
    independent: bool = True  # if False, cannot be invoked directly via --type
    required: list[str] = field(default_factory=list)
    skippable: list[str] = field(default_factory=list)
    phase_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for p in self.phases:
            name = p["name"]
            self.phase_names.append(name)
            (self.skippable if p.get("skippable") else self.required).append(name)


@dataclass
class DisplayConfig:
    separator: str
    separator_width: int
    header_char: str
    header_width: int


@dataclass
class BannerConfig:
    header: str
    progress_current: str
    progress_done: str


@dataclass
class FooterConfig:
    start: str
    end: str
    final: str


@dataclass
class CliConfig:
    description: str
    epilog: str
    commands: dict[str, str]
    args: dict[str, str]


@dataclass
class AppConfig:
    name: str
    description: str
    cmd: str
    artifacts_dir: str
    display: DisplayConfig
    banner: BannerConfig
    footer: FooterConfig
    messages: dict[str, str]
    cli: CliConfig


@dataclass
class Model:
    workflow_types: dict[str, WorkflowType]
    phases: dict[str, Phase]
    agents: dict[str, list[Agent]]  # phase key -> agents (FULL::RESEARCH, FULL::HYPOTHESIS, etc.)
    gates: dict[str, Gate]  # readback, gatekeeper, gatekeeper_skip, gatekeeper_force_skip
    app: AppConfig
    actions: dict[str, ActionDef] = field(default_factory=dict)
    # Gate lifecycle metadata: which gate types belong to which lifecycle point
    # Populated during model loading from on_start/on_end/on_skip YAML structure
    start_gate_types: set[str] = field(default_factory=set)
    end_gate_types: set[str] = field(default_factory=set)
    skip_gate_types: set[str] = field(default_factory=set)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required resource file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        try:
            return yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Malformed YAML in {path}: {exc}") from exc


# ── Builder functions ─────────────────────────────────────────────────────────


_WORKFLOW_RESERVED_KEYS = {"actions"}


def _build_workflow_types(raw: dict) -> dict[str, WorkflowType]:
    result: dict[str, WorkflowType] = {}
    for key, val in raw.items():
        if not isinstance(val, dict) or key in _WORKFLOW_RESERVED_KEYS:
            continue
        result[key] = WorkflowType(
            description=val.get("description", ""),
            phases=val.get("phases", []),
            cli_name=val.get("cli_name", ""),
            depends_on=val.get("depends_on", ""),
            independent=val.get("independent", True),
        )
    return result


_PHASE_RESERVED_KEYS = {"shared_gates"}


def _build_phases(raw: dict) -> dict[str, Phase]:
    return {
        key: Phase(**{k: val[k] for k in Phase.__dataclass_fields__ if k in val and k != "gates"})
        for key, val in raw.items()
        if isinstance(val, dict) and key not in _PHASE_RESERVED_KEYS
    }


def _build_agents_and_gates(
    raw: dict,
) -> tuple[dict[str, list[Agent]], dict[str, Gate], set[str], set[str], set[str]]:
    """Build agent lists and gate definitions from phases.yaml.

    Returns (agents, gates, start_gate_types, end_gate_types, skip_gate_types).
    The gate type sets record which gate types appear under each lifecycle point
    (on_start, on_end, on_skip) so the orchestrator can discover gate names from
    the model instead of hardcoding them.
    """
    agents: dict[str, list[Agent]] = {}
    gates: dict[str, Gate] = {}
    _LIFECYCLE_MAP = {"on_start": "start", "on_end": "end", "on_skip": "skip"}
    gate_type_sets: dict[str, set[str]] = {"start": set(), "end": set(), "skip": set()}
    for phase_key, section in raw.items():
        if not isinstance(section, dict):
            continue
        if phase_key == "shared_gates":
            # Shared gates live under lifecycle subsections (on_skip)
            for lifecycle, subsection in section.items():
                if not isinstance(subsection, dict):
                    continue
                bucket = _LIFECYCLE_MAP.get(lifecycle, lifecycle)
                for gk, gv in subsection.items():
                    if not isinstance(gv, dict):
                        continue
                    gates[gk] = Gate(
                        mode=gv.get("mode", "standalone_session"),
                        description=gv.get("description", ""),
                        prompt=gv.get("prompt", ""),
                    )
                    gate_type_sets.get(bucket, set()).add(gk)
        else:
            # Backward compat: agents at phase level
            agent_list = section.get("agents", [])
            # Gates live under lifecycle subsections (on_start, on_end)
            for lifecycle, subsection in section.get("gates", {}).items():
                if not isinstance(subsection, dict):
                    continue
                bucket = _LIFECYCLE_MAP.get(lifecycle, lifecycle)
                # Agents inside on_end take precedence over phase-level
                if lifecycle == "on_end" and "agents" in subsection:
                    agent_list = subsection["agents"]
                for gate_type, gate_def in subsection.items():
                    if gate_type == "agents":
                        continue  # agents list, not a gate
                    if isinstance(gate_def, dict):
                        gates[f"{phase_key}::{gate_type}"] = Gate(
                            mode=gate_def.get("mode", "standalone_session"),
                            description=gate_def.get("description", ""),
                            prompt=gate_def.get("prompt", ""),
                        )
                        gate_type_sets.get(bucket, set()).add(gate_type)
            if agent_list:
                agents[phase_key] = [
                    Agent(
                        name=a["name"],
                        display_name=a["display_name"],
                        prompt=a.get("prompt", ""),
                        mode=a.get("mode", ""),
                        checklist=a.get("checklist"),
                    )
                    for a in agent_list
                ]
    return agents, gates, gate_type_sets["start"], gate_type_sets["end"], gate_type_sets["skip"]


def _build_app(raw: dict) -> AppConfig:
    app, dis, ban, ftr, cli = (
        raw.get(k, {}) for k in ("app", "display", "banner", "footer", "cli")
    )
    return AppConfig(
        name=app.get("name", ""),
        description=app.get("description", ""),
        cmd=app.get("cmd", ""),
        artifacts_dir=app.get("artifacts_dir", ".auto-build-claw"),
        display=DisplayConfig(
            separator=dis.get("separator", "─"),
            separator_width=dis.get("separator_width", 70),
            header_char=dis.get("header_char", "="),
            header_width=dis.get("header_width", 70),
        ),
        banner=BannerConfig(
            header=ban.get("header", ""),
            progress_current=ban.get("progress_current", "**{p}**"),
            progress_done=ban.get("progress_done", "~~{p}~~"),
        ),
        footer=FooterConfig(
            start=ftr.get("start", ""), end=ftr.get("end", ""), final=ftr.get("final", "")
        ),
        messages=raw.get("messages", {}),
        cli=CliConfig(
            description=cli.get("description", ""),
            epilog=cli.get("epilog", ""),
            commands=cli.get("commands", {}),
            args=cli.get("args", {}),
        ),
    )


def _build_actions(raw: dict) -> dict[str, ActionDef]:
    """Build action definitions from workflow.yaml's optional actions section."""
    actions_raw = raw.get("actions", {})
    if not isinstance(actions_raw, dict):
        return {}
    result: dict[str, ActionDef] = {}
    for name, defn in actions_raw.items():
        if not isinstance(defn, dict):
            continue
        result[name] = ActionDef(
            type=defn.get("type", "programmatic"),
            description=defn.get("description", ""),
            prompt=defn.get("prompt", ""),
            cli_name=defn.get("cli_name", ""),
        )
    return result


# ── Public API ────────────────────────────────────────────────────────────────


def load_model(resources_dir: str | Path) -> Model:
    """Load all YAML resource files and return a Model object."""
    base = Path(resources_dir)
    wf_raw = _load_yaml(base / "workflow.yaml")
    ph_raw = _load_yaml(base / "phases.yaml")
    app_raw = _load_yaml(base / "app.yaml")
    # Agents and gates are now inline in phases.yaml
    agents, gates, start_gates, end_gates, skip_gates = _build_agents_and_gates(ph_raw)

    return Model(
        workflow_types=_build_workflow_types(wf_raw),
        phases=_build_phases(ph_raw),
        agents=agents,
        gates=gates,
        app=_build_app(app_raw),
        actions=_build_actions(wf_raw),
        start_gate_types=start_gates,
        end_gate_types=end_gates,
        skip_gate_types=skip_gates,
    )


_VALID_MODES = {"", "standalone_session"}
_KNOWN_VARS = {
    "objective",
    "iteration",
    "iteration_purpose",
    "workflow_type",
    "prior_context",
    "plan_context",
    "prior_hyp",
    "CMD",
    "cmd",
    "checklist",
    "benchmark_info",
    "remaining",
    "total",
    "agents_instructions",
    "spawn_instruction",
    "spawn_instruction_plan",
    "phase",
    "nxt",
    "iter_label",
    "itype",
    "action",
    "phase_idx",
    "reject_info",
    "progress",
    "separator_line",
    "header_line",
    "description",
    "understanding",
    "instructions",
    "exit_criteria",
    "required_agents",
    "recorded_agents",
    "output_status",
    "readback_status",
    "benchmark_configured",
    "evidence",
    "reason",
    "completed_phases",
    "phase_purpose",
    "p",
}
_GATE_REQUIRED_VARS: dict[str, list[str]] = {
    "readback": ["understanding"],
    "gatekeeper": ["evidence"],
    "gatekeeper_skip": ["phase", "iteration", "itype", "objective", "reason"],
    "gatekeeper_force_skip": ["phase", "iteration", "reason"],
}


def resolve_phase_key(workflow: str, phase: str, registry: set) -> str:
    """Resolve a namespaced phase key with strict lookup.

    Resolution order: WORKFLOW::PHASE -> bare PHASE.
    No fallback to other workflows. Missing key = configuration error.
    """
    namespaced = f"{workflow.upper()}::{phase}"
    if namespaced in registry:
        return namespaced
    if phase in registry:
        return phase
    raise KeyError(
        f"Phase '{phase}' not found for workflow '{workflow}'. "
        f"Tried '{namespaced}' and '{phase}'. "
        f"Available: {sorted(registry)}"
    )


def _resolve_key_lenient(workflow: str, phase: str, registry: set) -> str | None:
    """Resolve a namespaced key leniently for validation (returns None if not found)."""
    namespaced = f"{workflow.upper()}::{phase}"
    if namespaced in registry:
        return namespaced
    if phase in registry:
        return phase
    return None


def validate_model(model: Model) -> list[str]:
    """Return list of issues found in the model. Empty list = valid."""
    issues: list[str] = []
    known_phases = set(model.phases.keys())

    # workflow_types: FQN format validation
    for wf_name in model.workflow_types:
        if not wf_name.startswith("WORKFLOW::"):
            issues.append(
                f"[workflow.yaml] '{wf_name}': workflow key must use FQN format 'WORKFLOW::NAME'. "
                f"Fix: rename to 'WORKFLOW::{wf_name.upper()}'."
            )

    # workflow_types: cli_name required and unique
    cli_names: dict[str, str] = {}
    for wf_name, wf in model.workflow_types.items():
        if not wf.cli_name:
            issues.append(
                f"[workflow.yaml] '{wf_name}': missing 'cli_name'. "
                "Fix: add 'cli_name: ...' to the workflow type."
            )
        elif wf.cli_name in cli_names:
            issues.append(
                f"[workflow.yaml] '{wf_name}': cli_name '{wf.cli_name}' conflicts with "
                f"'{cli_names[wf.cli_name]}'. Fix: use unique cli_names."
            )
        else:
            cli_names[wf.cli_name] = wf_name

    # workflow_types: required fields and phase names resolve (namespaced or bare)
    for wf_name, wf in model.workflow_types.items():
        if not wf.description:
            issues.append(
                f"[workflow.yaml] '{wf_name}': missing 'description'. "
                "Fix: add 'description: ...' to the workflow type."
            )
        # depends_on must use FQN if set
        if wf.depends_on and not wf.depends_on.startswith("WORKFLOW::"):
            issues.append(
                f"[workflow.yaml] '{wf_name}': depends_on '{wf.depends_on}' must use FQN format "
                f"'WORKFLOW::...'. Fix: rename to 'WORKFLOW::{wf.depends_on.upper()}'."
            )
        # depends_on must reference an existing workflow
        if wf.depends_on and wf.depends_on not in model.workflow_types:
            issues.append(
                f"[workflow.yaml] '{wf_name}': depends_on '{wf.depends_on}' not found. "
                f"Available: {sorted(model.workflow_types.keys())}."
            )
        # Extract workflow prefix from FQN (WORKFLOW::FULL -> FULL)
        wf_prefix = wf_name.split("::", 1)[1] if "::" in wf_name else wf_name
        for p in wf.phases:
            if not isinstance(p, dict) or "name" not in p:
                issues.append(
                    f"[workflow.yaml] '{wf_name}.phases': entry missing 'name'. "
                    "Fix: add 'name: PHASE_NAME' to every phase entry."
                )
            else:
                resolved = _resolve_key_lenient(wf_prefix, p["name"], known_phases)
                if resolved is None:
                    issues.append(
                        f"[workflow.yaml] '{wf_name}': phase '{p['name']}' not found "
                        f"as '{wf_prefix.upper()}::{p['name']}' or '{p['name']}' in phases.yaml. "
                        "Fix: add the phase to phases.yaml or correct the name."
                    )

    # agents: keys must be namespaced (WORKFLOW::PHASE) or match a known phase
    for phase_key in model.agents:
        # Accept any key with :: (namespaced) or bare keys matching phases
        if "::" not in phase_key and phase_key not in known_phases:
            issues.append(
                f"[phases.yaml] section '{phase_key}' has no matching phase in phases.yaml. "
                "Fix: rename to match a phases.yaml key or use WORKFLOW::PHASE notation."
            )

    # agents: mode values, unique names, required fields
    for phase_key, agent_list in model.agents.items():
        seen_names: set[str] = set()
        for agent in agent_list:
            if agent.mode not in _VALID_MODES:
                issues.append(
                    f"[phases.yaml] '{phase_key}.{agent.name}': invalid mode '{agent.mode}'. "
                    "Fix: use '' or 'standalone_session'."
                )
            if agent.name in seen_names:
                issues.append(
                    f"[phases.yaml] '{phase_key}': duplicate agent name '{agent.name}'. "
                    "Fix: use unique names within each phase."
                )
            seen_names.add(agent.name)
            for f in ("name", "display_name", "prompt"):
                if not getattr(agent, f):
                    issues.append(
                        f"[phases.yaml] '{phase_key}.{agent.name}': missing '{f}'. "
                        f"Fix: add '{f}: ...' to the agent entry."
                    )
            if agent.checklist is not None:
                if "VERDICTS:" not in agent.checklist:
                    issues.append(
                        f"[phases.yaml] '{phase_key}.{agent.name}.checklist': missing 'VERDICTS:'. "
                        "Fix: add 'VERDICTS: CLEAN / WARN / BLOCK / ASK'."
                    )
                if len(re.findall(r"^\s*\d+\.", agent.checklist, re.MULTILINE)) < 4:
                    issues.append(
                        f"[phases.yaml] '{phase_key}.{agent.name}.checklist': fewer than 4 numbered items. "
                        "Fix: checklist must have exactly 4 numbered items."
                    )

    # phases: template variables are from known set
    for phase_name, phase in model.phases.items():
        for attr in Phase.__dataclass_fields__:
            text = getattr(phase, attr)
            if text and isinstance(text, str):
                for var in re.findall(r"\{(\w+)\}", text):
                    if var not in _KNOWN_VARS:
                        issues.append(
                            f"[phases.yaml] '{phase_name}.{attr}': unknown variable '{{{var}}}'. "
                            "Fix: add it to _KNOWN_VARS or correct the placeholder."
                        )

    # phases: reject_to targets must reference valid phases in some workflow
    for phase_name, phase in model.phases.items():
        if phase.reject_to:
            target = phase.reject_to.get("phase", "")
            if target and target not in known_phases:
                # Check if any namespaced version exists
                found = any(k.endswith(f"::{target}") for k in known_phases)
                if not found:
                    issues.append(
                        f"[phases.yaml] '{phase_name}.reject_to': target phase '{target}' not found. "
                        "Fix: use a valid phase name from phases.yaml."
                    )

    # phases: auto_action names should reference valid actions by cli_name
    # Build cli_name -> FQN lookup for actions
    action_cli_names = set()
    for action_fqn, action_def in model.actions.items():
        if action_def.cli_name:
            action_cli_names.add(action_def.cli_name)
    known_actions = action_cli_names if action_cli_names else set(model.actions.keys())
    for phase_name, phase in model.phases.items():
        if phase.auto_actions:
            for action in phase.auto_actions.get("on_complete", []):
                if action not in known_actions:
                    issues.append(
                        f"[phases.yaml] '{phase_name}.auto_actions': unknown action '{action}'. "
                        f"Known cli_names: {', '.join(sorted(known_actions))}."
                    )

    # planning workflow: verify PLANNING::PLAN exists
    planning_wf = model.workflow_types.get("WORKFLOW::PLANNING")
    if planning_wf:
        for p in planning_wf.phases:
            if isinstance(p, dict) and p.get("name") == "PLAN":
                if "PLANNING::PLAN" not in known_phases:
                    issues.append(
                        "[phases.yaml] planning workflow PLAN phase: 'PLANNING::PLAN' not found. "
                        "Fix: add a PLANNING::PLAN entry to phases.yaml."
                    )
                break

    # actions: FQN format validation
    for action_name in model.actions:
        if not action_name.startswith("ACTION::"):
            issues.append(
                f"[workflow.yaml] action '{action_name}': must use FQN format 'ACTION::NAME'. "
                f"Fix: rename to 'ACTION::{action_name.upper()}'."
            )

    # actions: cli_name required and unique
    action_cli_map: dict[str, str] = {}
    for action_name, action_def in model.actions.items():
        if not action_def.cli_name:
            issues.append(
                f"[workflow.yaml] action '{action_name}': missing 'cli_name'. "
                "Fix: add 'cli_name: ...' to the action definition."
            )
        elif action_def.cli_name in action_cli_map:
            issues.append(
                f"[workflow.yaml] action '{action_name}': cli_name '{action_def.cli_name}' "
                f"conflicts with '{action_cli_map[action_def.cli_name]}'. Fix: use unique cli_names."
            )
        else:
            action_cli_map[action_def.cli_name] = action_name

    # gates: required placeholders present in prompt (namespaced keys)
    for gate_key, gate in model.gates.items():
        # Extract gate type from namespaced key: "FULL::RESEARCH::readback" -> "readback"
        gate_type = gate_key.rsplit("::", 1)[-1] if "::" in gate_key else gate_key
        for var in _GATE_REQUIRED_VARS.get(gate_type, []):
            if f"{{{var}}}" not in gate.prompt:
                issues.append(
                    f"[phases.yaml] '{gate_key}': missing placeholder '{{{var}}}'. "
                    "Fix: add it to the gate prompt template."
                )

    # gates: every workflow phase must resolve to both start and end gate types
    # Gate types are discovered from lifecycle metadata (on_start/on_end) rather
    # than hardcoded, making validation match whatever gate types the YAML defines
    required_gate_types = model.start_gate_types | model.end_gate_types
    gate_phase_keys = set()
    for gk in model.gates:
        parts = gk.rsplit("::", 1)
        if len(parts) == 2 and parts[1] in required_gate_types:
            gate_phase_keys.add(parts[0])
    for wf_name, wf in model.workflow_types.items():
        # Extract workflow prefix from FQN
        wf_prefix = wf_name.split("::", 1)[1] if "::" in wf_name else wf_name
        for p in wf.phases:
            if not isinstance(p, dict) or "name" not in p:
                continue
            resolved = _resolve_key_lenient(wf_prefix, p["name"], gate_phase_keys)
            if resolved is None:
                for gate_type in required_gate_types:
                    issues.append(
                        f"[phases.yaml] workflow '{wf_name}' phase '{p['name']}': "
                        f"no {gate_type} gate found (tried '{wf_prefix.upper()}::{p['name']}::{gate_type}', "
                        f"'{p['name']}::{gate_type}'). "
                        f"Fix: add gates.{gate_type} to the phase section in phases.yaml."
                    )
            else:
                for gate_type in required_gate_types:
                    gate_key = f"{resolved}::{gate_type}"
                    if gate_key not in model.gates:
                        issues.append(
                            f"[phases.yaml] workflow '{wf_name}' phase '{p['name']}': "
                            f"no {gate_type} gate found at '{gate_key}'. "
                            f"Fix: add gates.{gate_type} to the phase section in phases.yaml."
                        )

    # gates: agent name references must match actual agents for the phase
    agent_keys = set(model.agents.keys())
    for gate_key, gate in model.gates.items():
        if "{required_agents}" not in gate.prompt:
            continue
        # Extract phase key from namespaced gate key: "FULL::RESEARCH::gatekeeper" -> "FULL::RESEARCH"
        parts = gate_key.rsplit("::", 1)
        if len(parts) < 2:
            continue
        phase_key = parts[0]
        # Check direct match
        if phase_key in agent_keys:
            continue
        # Try bare phase name
        wf_parts = phase_key.split("::", 1)
        bare = wf_parts[-1] if len(wf_parts) == 2 else phase_key
        if bare in agent_keys:
            continue
        issues.append(
            f"[phases.yaml] '{gate_key}': prompt references {{required_agents}} "
            f"but phase '{phase_key}' has no agents defined. "
            "Fix: add agents to the phase or remove the {{required_agents}} placeholder."
        )

    # app: required fields
    for field_name, val in (("name", model.app.name), ("cmd", model.app.cmd)):
        if not val:
            issues.append(
                f"[app.yaml] 'app.{field_name}': missing. Fix: add '{field_name}: ...' under app:."
            )

    return issues
