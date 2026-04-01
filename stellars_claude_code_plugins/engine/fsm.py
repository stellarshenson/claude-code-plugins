"""Finite State Machine engine for phase lifecycle management.

Built on the `transitions` Python package. Each phase goes through states
(pending -> readback -> in_progress -> gatekeeper -> complete) with
transitions triggered by events (start, end, reject, skip).

Guards are conditions checked before a transition fires.
Actions are side effects triggered after a transition completes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from transitions import Machine, MachineError


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


class FSM:
    """Finite state machine for phase lifecycle.

    Wraps transitions.Machine with a stable interface for the orchestrator.
    Guards are checked before transitions fire. Actions run after transitions
    complete. Every transition is logged.
    """

    def __init__(self, transitions_list: list[dict]):
        self._guards: dict[str, Callable] = {}
        self._actions: dict[str, Callable] = {}
        self._log: list[dict] = []
        self._context: dict = {}

        states = [s.value for s in State]
        self._machine = Machine(
            model=self,
            states=states,
            initial=State.PENDING.value,
            auto_transitions=False,
            send_event=True,
        )

        for t in transitions_list:
            trigger = t["trigger"]
            source = t["source"]
            dest = t["dest"]
            guard = t.get("guard", "")
            action = t.get("action", "")

            conditions = []
            if guard:
                conditions.append(lambda evt, g=guard: self._evaluate_guard(g, self._context))

            after = []
            after.append(lambda evt, s=source, tr=trigger, d=dest, g=guard, a=action:
                         self._log_transition(s, tr, d, g, a))
            if action:
                after.append(lambda evt, a=action: self._execute_action(a, self._context))

            self._machine.add_transition(
                trigger=trigger,
                source=source,
                dest=dest,
                conditions=conditions,
                after=after,
            )

    @property
    def current_state(self) -> State:
        return State(self.state)

    @current_state.setter
    def current_state(self, state: State) -> None:
        self._machine.set_state(state.value if isinstance(state, State) else state)

    def register_guard(self, name: str, fn: Callable[..., bool]) -> None:
        """Register a named guard function."""
        self._guards[name] = fn

    def register_action(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a named action function."""
        self._actions[name] = fn

    def can_fire(self, event: str | Event, **context) -> bool:
        """Check if an event can fire in the current state."""
        event_str = event.value if isinstance(event, Event) else event
        self._context = context
        return self._machine.get_triggers(self.state).__contains__(event_str) and \
            self._try_conditions(event_str)

    def fire(self, event: str | Event, **context) -> State:
        """Fire an event, executing the matching transition.

        Raises ValueError if no valid transition exists or all guards fail.
        """
        event_str = event.value if isinstance(event, Event) else event
        self._context = context
        old_state = self.state
        log_len = len(self._log)
        try:
            self.trigger(event_str)
        except (MachineError, AttributeError) as e:
            raise ValueError(str(e)) from e
        # transitions silently stays in state when all conditions fail
        if self.state == old_state and len(self._log) == log_len:
            raise ValueError(
                f"All guards failed for transition from '{old_state}' "
                f"on event '{event_str}'."
            )
        return self.current_state

    def reset(self, state: State = State.PENDING) -> None:
        """Reset FSM to a given state."""
        self.current_state = state

    @property
    def log(self) -> list[dict]:
        """Return the transition log."""
        return self._log

    def simulate(self, workflow_phases: list[str], **context) -> list[dict]:
        """Simulate a full workflow run without executing actions.

        Walks through all phases, firing events in sequence to verify
        the transition graph is complete.
        """
        reports = []
        saved_state = self.state
        saved_actions = dict(self._actions)
        self._actions = {k: lambda **ctx: None for k in saved_actions}

        try:
            for phase in workflow_phases:
                report = {"phase": phase, "transitions": [], "valid": True}
                self.reset(State.PENDING)

                for event in [Event.START, Event.READBACK_PASS, Event.END,
                              Event.GATE_PASS, Event.ADVANCE]:
                    try:
                        old = self.state
                        self.fire(event, phase=phase, **context)
                        report["transitions"].append({
                            "event": event.value,
                            "from": old,
                            "to": self.state,
                        })
                    except ValueError as e:
                        report["valid"] = False
                        report["error"] = str(e)
                        break

                reports.append(report)
        finally:
            self._machine.set_state(saved_state)
            self._actions = saved_actions

        return reports

    def _try_conditions(self, event_str: str) -> bool:
        """Check if any transition for this event passes its conditions."""
        transitions = self._machine.get_transitions(
            trigger=event_str, source=self.state
        )
        for t in transitions:
            if not t.conditions:
                return True
            if all(c.check(self) for c in t.conditions):
                return True
        return False

    def _log_transition(self, source: str, trigger: str, dest: str,
                        guard: str, action: str) -> None:
        """Record a transition in the audit log."""
        self._log.append({
            "from": source,
            "event": trigger,
            "to": dest,
            "guard": guard,
            "action": action,
        })

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
        {"trigger": "start", "source": "pending", "dest": "readback"},
        {"trigger": "readback_pass", "source": "readback", "dest": "in_progress"},
        {"trigger": "readback_fail", "source": "readback", "dest": "pending"},
        {"trigger": "end", "source": "in_progress", "dest": "gatekeeper"},
        {"trigger": "gate_pass", "source": "gatekeeper", "dest": "complete"},
        {"trigger": "gate_fail", "source": "gatekeeper", "dest": "in_progress"},
        {"trigger": "skip", "source": "pending", "dest": "skipped"},
        {"trigger": "reject", "source": "in_progress", "dest": "rejected"},
        {"trigger": "advance", "source": "rejected", "dest": "pending"},
        {"trigger": "advance", "source": "complete", "dest": "pending"},
        {"trigger": "advance", "source": "skipped", "dest": "pending"},
    ]
    return FSM(transitions)


def resolve_phase_key(workflow_type: str, phase_name: str, registry: dict) -> str:
    """Resolve a namespaced phase key with fallback to bare name.

    Tries WORKFLOW::PHASE first (e.g., FULL::RESEARCH), then falls back
    to bare PHASE (e.g., RESEARCH) for shared phases like RECORD/NEXT.
    """
    namespaced = f"{workflow_type.upper()}::{phase_name}"
    if namespaced in registry:
        return namespaced
    return phase_name
