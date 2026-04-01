"""Finite State Machine engine for phase lifecycle management.

Drives phase transitions declaratively from YAML configuration instead
of imperative if/else branches in the orchestrator. Each phase goes
through states (pending -> readback -> in_progress -> gatekeeper ->
complete) with transitions triggered by events (start, end, reject, skip).

Guards are conditions checked before a transition fires.
Actions are side effects triggered after a transition completes.
Both are referenced by name in YAML and resolved to callables at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class State(str, Enum):
    """Phase lifecycle states."""
    PENDING = "pending"
    READBACK = "readback"
    IN_PROGRESS = "in_progress"
    GATEKEEPER = "gatekeeper"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    REJECTED = "rejected"


class Event(str, Enum):
    """Events that trigger state transitions."""
    START = "start"
    READBACK_PASS = "readback_pass"
    READBACK_FAIL = "readback_fail"
    END = "end"
    GATE_PASS = "gate_pass"
    GATE_FAIL = "gate_fail"
    REJECT = "reject"
    SKIP = "skip"
    ADVANCE = "advance"


@dataclass
class Transition:
    """A single state transition rule."""
    from_state: str
    event: str
    to_state: str
    guard: str = ""
    action: str = ""


@dataclass
class FSMConfig:
    """FSM configuration loaded from YAML."""
    transitions: list[Transition] = field(default_factory=list)
    guards: dict[str, str] = field(default_factory=dict)
    actions: dict[str, str] = field(default_factory=dict)


class FSM:
    """Finite state machine for phase lifecycle.

    Loads transitions from configuration, validates them, and executes
    state changes. Guards are checked before transitions fire. Actions
    run after transitions complete. Every transition is logged.

    The FSM does NOT own output formatting or user-facing display.
    It owns state transitions only. The orchestrator calls fire() and
    handles display around it.
    """

    def __init__(self, config: FSMConfig):
        self._transitions = config.transitions
        self._guards: dict[str, Callable] = {}
        self._actions: dict[str, Callable] = {}
        self._log: list[dict] = []
        self._current_state = State.PENDING

        # Build transition lookup: (from_state, event) -> list[Transition]
        self._lookup: dict[tuple[str, str], list[Transition]] = {}
        for t in self._transitions:
            key = (t.from_state, t.event)
            self._lookup.setdefault(key, []).append(t)

    @property
    def current_state(self) -> State:
        return self._current_state

    @current_state.setter
    def current_state(self, state: State) -> None:
        self._current_state = state

    def register_guard(self, name: str, fn: Callable[..., bool]) -> None:
        """Register a named guard function."""
        self._guards[name] = fn

    def register_action(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a named action function."""
        self._actions[name] = fn

    def can_fire(self, event: str | Event, **context) -> bool:
        """Check if an event can fire in the current state."""
        event_str = event.value if isinstance(event, Event) else event
        key = (self._current_state.value, event_str)
        transitions = self._lookup.get(key, [])
        for t in transitions:
            if not t.guard or self._evaluate_guard(t.guard, context):
                return True
        return False

    def fire(self, event: str | Event, **context) -> State:
        """Fire an event, executing the matching transition.

        Checks guards, updates state, runs actions, logs the transition.
        Raises ValueError if no valid transition exists.
        """
        event_str = event.value if isinstance(event, Event) else event
        key = (self._current_state.value, event_str)
        transitions = self._lookup.get(key, [])

        if not transitions:
            raise ValueError(
                f"No transition from state '{self._current_state.value}' "
                f"on event '{event_str}'. Valid events: "
                f"{[e for (s, e) in self._lookup if s == self._current_state.value]}"
            )

        # Find first transition whose guard passes
        for t in transitions:
            if t.guard and not self._evaluate_guard(t.guard, context):
                continue

            old_state = self._current_state
            self._current_state = State(t.to_state)

            # Log transition
            self._log.append({
                "from": old_state.value,
                "event": event_str,
                "to": self._current_state.value,
                "guard": t.guard,
                "action": t.action,
            })

            # Run action if defined
            if t.action:
                self._execute_action(t.action, context)

            return self._current_state

        raise ValueError(
            f"All guards failed for transition from '{self._current_state.value}' "
            f"on event '{event_str}'."
        )

    def reset(self, state: State = State.PENDING) -> None:
        """Reset FSM to a given state."""
        self._current_state = state

    @property
    def log(self) -> list[dict]:
        """Return the transition log."""
        return self._log

    def simulate(self, workflow_phases: list[str], **context) -> list[dict]:
        """Simulate a full workflow run without executing actions.

        Walks through all phases, firing events in sequence to verify
        the transition graph is complete. Returns a list of phase
        reports for dry-run output.
        """
        reports = []
        saved_state = self._current_state
        saved_actions = dict(self._actions)
        # Disable actions during simulation
        self._actions = {k: lambda **ctx: None for k in saved_actions}

        try:
            for phase in workflow_phases:
                report = {"phase": phase, "transitions": [], "valid": True}
                self.reset(State.PENDING)

                # Simulate: pending -> start -> readback_pass -> end -> gate_pass -> advance
                for event in [Event.START, Event.READBACK_PASS, Event.END,
                              Event.GATE_PASS, Event.ADVANCE]:
                    try:
                        old = self._current_state.value
                        self.fire(event, phase=phase, **context)
                        report["transitions"].append({
                            "event": event.value,
                            "from": old,
                            "to": self._current_state.value,
                        })
                    except ValueError as e:
                        report["valid"] = False
                        report["error"] = str(e)
                        break

                reports.append(report)
        finally:
            self._current_state = saved_state
            self._actions = saved_actions

        return reports

    def _evaluate_guard(self, guard_name: str, context: dict) -> bool:
        """Evaluate a named guard with the given context."""
        guard_fn = self._guards.get(guard_name)
        if guard_fn is None:
            raise ValueError(f"Unknown guard: '{guard_name}'. "
                           f"Registered: {list(self._guards.keys())}")
        return guard_fn(**context)

    def _execute_action(self, action_name: str, context: dict) -> None:
        """Execute a named action with the given context."""
        action_fn = self._actions.get(action_name)
        if action_fn is None:
            raise ValueError(f"Unknown action: '{action_name}'. "
                           f"Registered: {list(self._actions.keys())}")
        action_fn(**context)


def build_phase_lifecycle_fsm() -> FSM:
    """Build the standard phase lifecycle FSM with universal transitions.

    Every phase follows the same lifecycle:
    pending -> readback -> in_progress -> gatekeeper -> complete
    With branches for: readback_fail (retry), gate_fail (retry),
    reject (back to implementation), skip (advance without executing).
    """
    transitions = [
        Transition("pending", "start", "readback"),
        Transition("readback", "readback_pass", "in_progress"),
        Transition("readback", "readback_fail", "pending"),
        Transition("in_progress", "end", "gatekeeper"),
        Transition("gatekeeper", "gate_pass", "complete"),
        Transition("gatekeeper", "gate_fail", "in_progress"),
        Transition("pending", "skip", "skipped"),
        Transition("in_progress", "reject", "rejected"),
        Transition("rejected", "advance", "pending"),
        Transition("complete", "advance", "pending"),
        Transition("skipped", "advance", "pending"),
    ]
    return FSM(FSMConfig(transitions=transitions))


def resolve_phase_key(workflow_type: str, phase_name: str, registry: dict) -> str:
    """Resolve a namespaced phase key with fallback to bare name.

    Tries WORKFLOW::PHASE first (e.g., FULL::RESEARCH), then falls back
    to bare PHASE (e.g., RESEARCH) for shared phases like RECORD/NEXT.
    """
    namespaced = f"{workflow_type.upper()}::{phase_name}"
    if namespaced in registry:
        return namespaced
    return phase_name
