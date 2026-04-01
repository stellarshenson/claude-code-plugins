"""Unit tests for the FSM engine (transitions-based)."""

import pytest

from stellars_claude_code_plugins.engine.fsm import (
    Event,
    FSM,
    State,
    build_phase_lifecycle_fsm,
    resolve_phase_key,
)


class TestFSMBasic:
    """Basic FSM construction and transition tests."""

    @pytest.fixture
    def simple_fsm(self):
        """Two-state FSM for basic testing."""
        return FSM([
            {"trigger": "start", "source": "pending", "dest": "in_progress"},
            {"trigger": "end", "source": "in_progress", "dest": "complete"},
        ])

    def test_initial_state(self, simple_fsm):
        assert simple_fsm.current_state == State.PENDING

    def test_fire_transition(self, simple_fsm):
        result = simple_fsm.fire(Event.START)
        assert result == State.IN_PROGRESS
        assert simple_fsm.current_state == State.IN_PROGRESS

    def test_fire_chain(self, simple_fsm):
        simple_fsm.fire(Event.START)
        result = simple_fsm.fire(Event.END)
        assert result == State.COMPLETE

    def test_fire_invalid_event_raises(self, simple_fsm):
        with pytest.raises(ValueError):
            simple_fsm.fire(Event.END)  # can't end from pending

    def test_fire_string_event(self, simple_fsm):
        result = simple_fsm.fire("start")
        assert result == State.IN_PROGRESS

    def test_can_fire_true(self, simple_fsm):
        assert simple_fsm.can_fire(Event.START) is True

    def test_can_fire_false(self, simple_fsm):
        assert simple_fsm.can_fire(Event.END) is False

    def test_reset(self, simple_fsm):
        simple_fsm.fire(Event.START)
        simple_fsm.reset()
        assert simple_fsm.current_state == State.PENDING

    def test_reset_to_specific_state(self, simple_fsm):
        simple_fsm.reset(State.COMPLETE)
        assert simple_fsm.current_state == State.COMPLETE

    def test_set_current_state(self, simple_fsm):
        simple_fsm.current_state = State.IN_PROGRESS
        assert simple_fsm.current_state == State.IN_PROGRESS

    def test_log_records_transitions(self, simple_fsm):
        simple_fsm.fire(Event.START)
        simple_fsm.fire(Event.END)
        assert len(simple_fsm.log) == 2
        assert simple_fsm.log[0]["from"] == "pending"
        assert simple_fsm.log[0]["to"] == "in_progress"
        assert simple_fsm.log[1]["from"] == "in_progress"
        assert simple_fsm.log[1]["to"] == "complete"


class TestFSMGuards:
    """Guard function tests."""

    @pytest.fixture
    def guarded_fsm(self):
        return FSM([
            {"trigger": "start", "source": "pending", "dest": "in_progress", "guard": "is_ready"},
            {"trigger": "start", "source": "pending", "dest": "rejected", "guard": "not_ready"},
        ])

    def test_guard_passes(self, guarded_fsm):
        guarded_fsm.register_guard("is_ready", lambda **ctx: True)
        guarded_fsm.register_guard("not_ready", lambda **ctx: False)
        result = guarded_fsm.fire(Event.START)
        assert result == State.IN_PROGRESS

    def test_guard_fails_tries_next(self, guarded_fsm):
        guarded_fsm.register_guard("is_ready", lambda **ctx: False)
        guarded_fsm.register_guard("not_ready", lambda **ctx: True)
        result = guarded_fsm.fire(Event.START)
        assert result == State.REJECTED

    def test_all_guards_fail_raises(self, guarded_fsm):
        guarded_fsm.register_guard("is_ready", lambda **ctx: False)
        guarded_fsm.register_guard("not_ready", lambda **ctx: False)
        with pytest.raises(ValueError):
            guarded_fsm.fire(Event.START)

    def test_unknown_guard_raises(self, guarded_fsm):
        with pytest.raises(ValueError, match="Unknown guard"):
            guarded_fsm.fire(Event.START)

    def test_guard_receives_context(self):
        fsm = FSM([
            {"trigger": "start", "source": "pending", "dest": "in_progress", "guard": "check_phase"},
        ])
        received = {}
        fsm.register_guard("check_phase", lambda **ctx: (received.update(ctx), True)[1])
        fsm.fire(Event.START, phase="RESEARCH", iteration=1)
        assert received["phase"] == "RESEARCH"
        assert received["iteration"] == 1


class TestFSMActions:
    """Action function tests."""

    def test_action_executed_on_transition(self):
        fsm = FSM([
            {"trigger": "start", "source": "pending", "dest": "in_progress", "action": "log_start"},
        ])
        called = []
        fsm.register_action("log_start", lambda **ctx: called.append("started"))
        fsm.fire(Event.START)
        assert called == ["started"]

    def test_unknown_action_raises(self):
        fsm = FSM([
            {"trigger": "start", "source": "pending", "dest": "in_progress", "action": "missing_action"},
        ])
        with pytest.raises(ValueError, match="Unknown action"):
            fsm.fire(Event.START)

    def test_action_receives_context(self):
        fsm = FSM([
            {"trigger": "start", "source": "pending", "dest": "in_progress", "action": "capture"},
        ])
        received = {}
        fsm.register_action("capture", lambda **ctx: received.update(ctx))
        fsm.fire(Event.START, phase="TEST", data="hello")
        assert received["phase"] == "TEST"
        assert received["data"] == "hello"


class TestPhaseLifecycleFSM:
    """Tests for the standard phase lifecycle FSM."""

    @pytest.fixture
    def lifecycle_fsm(self):
        return build_phase_lifecycle_fsm()

    def test_happy_path(self, lifecycle_fsm):
        """Full successful phase: pending -> readback -> in_progress -> gatekeeper -> complete."""
        lifecycle_fsm.fire(Event.START)
        assert lifecycle_fsm.current_state == State.READBACK

        lifecycle_fsm.fire(Event.READBACK_PASS)
        assert lifecycle_fsm.current_state == State.IN_PROGRESS

        lifecycle_fsm.fire(Event.END)
        assert lifecycle_fsm.current_state == State.GATEKEEPER

        lifecycle_fsm.fire(Event.GATE_PASS)
        assert lifecycle_fsm.current_state == State.COMPLETE

    def test_readback_fail_returns_to_pending(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_FAIL)
        assert lifecycle_fsm.current_state == State.PENDING

    def test_gate_fail_returns_to_in_progress(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_PASS)
        lifecycle_fsm.fire(Event.END)
        lifecycle_fsm.fire(Event.GATE_FAIL)
        assert lifecycle_fsm.current_state == State.IN_PROGRESS

    def test_reject_from_in_progress(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_PASS)
        lifecycle_fsm.fire(Event.REJECT)
        assert lifecycle_fsm.current_state == State.REJECTED

    def test_advance_from_rejected(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_PASS)
        lifecycle_fsm.fire(Event.REJECT)
        lifecycle_fsm.fire(Event.ADVANCE)
        assert lifecycle_fsm.current_state == State.PENDING

    def test_skip_from_pending(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.SKIP)
        assert lifecycle_fsm.current_state == State.SKIPPED

    def test_advance_from_skipped(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.SKIP)
        lifecycle_fsm.fire(Event.ADVANCE)
        assert lifecycle_fsm.current_state == State.PENDING

    def test_advance_from_complete(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_PASS)
        lifecycle_fsm.fire(Event.END)
        lifecycle_fsm.fire(Event.GATE_PASS)
        lifecycle_fsm.fire(Event.ADVANCE)
        assert lifecycle_fsm.current_state == State.PENDING

    def test_readback_retry_loop(self, lifecycle_fsm):
        """Readback can fail and retry multiple times."""
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_FAIL)
        assert lifecycle_fsm.current_state == State.PENDING

        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_FAIL)
        assert lifecycle_fsm.current_state == State.PENDING

        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_PASS)
        assert lifecycle_fsm.current_state == State.IN_PROGRESS

    def test_gate_retry_loop(self, lifecycle_fsm):
        """Gatekeeper can fail and retry multiple times."""
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.fire(Event.READBACK_PASS)
        lifecycle_fsm.fire(Event.END)
        lifecycle_fsm.fire(Event.GATE_FAIL)
        assert lifecycle_fsm.current_state == State.IN_PROGRESS

        lifecycle_fsm.fire(Event.END)
        lifecycle_fsm.fire(Event.GATE_FAIL)
        assert lifecycle_fsm.current_state == State.IN_PROGRESS

        lifecycle_fsm.fire(Event.END)
        lifecycle_fsm.fire(Event.GATE_PASS)
        assert lifecycle_fsm.current_state == State.COMPLETE

    def test_simulate_workflow(self, lifecycle_fsm):
        """Simulate runs through all phases without side effects."""
        reports = lifecycle_fsm.simulate(["RESEARCH", "PLAN", "IMPLEMENT"])
        assert len(reports) == 3
        for r in reports:
            assert r["valid"] is True
            assert len(r["transitions"]) == 5

    def test_simulate_preserves_state(self, lifecycle_fsm):
        lifecycle_fsm.fire(Event.START)
        lifecycle_fsm.simulate(["ALPHA", "BETA"])
        assert lifecycle_fsm.current_state == State.READBACK


class TestResolvePhaseKey:
    """Tests for resolve_phase_key namespace resolution."""

    def test_namespaced_match(self):
        registry = {"FULL::RESEARCH": "x", "RESEARCH": "y"}
        assert resolve_phase_key("full", "RESEARCH", registry) == "FULL::RESEARCH"

    def test_bare_fallback(self):
        registry = {"RECORD": "x"}
        assert resolve_phase_key("full", "RECORD", registry) == "RECORD"

    def test_no_match_returns_bare(self):
        registry = {"OTHER": "x"}
        assert resolve_phase_key("full", "MISSING", registry) == "MISSING"

    def test_case_insensitive_workflow(self):
        registry = {"HOTFIX::FIX": "x"}
        assert resolve_phase_key("hotfix", "FIX", registry) == "HOTFIX::FIX"
